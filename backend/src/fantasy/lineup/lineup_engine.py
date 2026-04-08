from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

from fantasy.intelligence.constants import POSITIONAL_CLIFF_AGE
from fantasy.intelligence.models import ScorecardInputs, TeamScorecard
from fantasy.intelligence.scorecard_engine import normalize_within_league
from fantasy.lineup.constants import (
    AGE_CLIFF_PROXIMITY_SEASONS,
    ELITE_INSULATION_THRESHOLD,
    ELITE_TARGET_PERCENTILE,
    FADING_WINDOW_THRESHOLD,
    LINEUP_CURRENT_STRENGTH_ADJUSTMENT_MULTIPLIER,
    LINEUP_CURRENT_STRENGTH_CEILING_WEIGHT,
    LINEUP_CURRENT_STRENGTH_FLOOR_WEIGHT,
    LINEUP_CURRENT_STRENGTH_MAX_ADJUSTMENT,
    LINEUP_CURRENT_STRENGTH_MIN_ADJUSTMENT,
    LINEUP_CURRENT_STRENGTH_SHORT_TERM_WEIGHT,
    LINEUP_TARGET_POOL_FRACTION,
    PLAYOFF_TARGET_PERCENTILE,
    PEAK_WINDOW_THRESHOLD,
    TE_NON_PREMIUM_URGENCY_WEIGHT,
    TITLE_TARGET_PERCENTILE,
    TITLE_WINDOW_WEIGHTS,
    UPGRADE_LEVERAGE_BASE_EQUITY,
)
from fantasy.lineup.models import LineupResult, LineupSlotScore
from fantasy.recommendation.card_engine import RecommendationCardEngine

_SLOT_SKIP = {"BN", "IR", "TAXI", "BENCH"}
_VALID_CONTEXT_FLAGS = (
    "qb_upgrade",
    "qb_downgrade",
    "coaching_change",
    "depth_chart_competition",
    "injury_recovery",
    "age_cliff_proximity",
    "role_expansion",
    "role_compression",
)


def _slot_skip(slot: str) -> bool:
    return slot.strip().upper() in _SLOT_SKIP


def _flex_like(slot: str) -> bool:
    return slot.strip().upper() in {"FLEX", "SUPER_FLEX", "SUPERFLEX", "S-FLEX"}


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 != 0:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    clamped = max(0.0, min(1.0, percentile))
    position = (len(ordered) - 1) * clamped
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float((ordered[lower] * (1.0 - weight)) + (ordered[upper] * weight))


def _top_tier_values(values: list[float]) -> list[float]:
    if len(values) < 2:
        return list(values)
    cutoff = max(2, math.ceil(len(values) * LINEUP_TARGET_POOL_FRACTION))
    return sorted(values, reverse=True)[:cutoff]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class SlotBenchmarkTargets:
    playoff_target: float
    title_target: float
    elite_target: float
    benchmark_used: bool
    benchmark_source: str
    benchmark_sample_size: int


@dataclass(frozen=True)
class CurrentStrengthSnapshot:
    current_production: float
    short_term: float
    ceiling: float
    floor: float


def _player_display(conn: duckdb.DuckDBPyConnection, player_id: str) -> str:
    try:
        row = conn.execute(
            "SELECT COALESCE(full_name, player_id) FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        return str(row[0]) if row else player_id
    except duckdb.Error:
        return player_id


def _te_premium_active(inputs: ScorecardInputs) -> bool:
    return bool(inputs.league_settings.get("te_premium", False))


class LineupEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._card_engine = RecommendationCardEngine(conn)

    def _base_current_strength_value(self, inputs: ScorecardInputs, player_id: str) -> float:
        if player_id in inputs.weekly_fantasy_pts:
            return float(inputs.weekly_fantasy_pts[player_id])
        position = inputs.player_positions.get(player_id, "UNKNOWN")
        med_avg = float(
            sum(inputs.position_medians.values())
            / max(len(inputs.position_medians), 1)
        )
        return float(inputs.position_medians.get(position, med_avg))

    def _load_current_strength_snapshots(
        self,
        all_inputs: dict[int, ScorecardInputs],
    ) -> dict[str, CurrentStrengthSnapshot]:
        player_ids = list(
            {
                player_id
                for inputs in all_inputs.values()
                for player_id in (inputs.starters + inputs.bench + inputs.ir + inputs.taxi)
                if player_id
            }
        )
        if not player_ids:
            return {}

        try:
            rows = self._conn.execute(
                """
                SELECT player_id, MAX(fantasy_points) AS best_week
                FROM player_stats_weekly
                WHERE player_id IN (
                    SELECT UNNEST(?)
                )
                GROUP BY player_id
                """,
                [player_ids],
            ).fetchall()
            best_week_by_player = {
                str(row[0]): float(row[1] or 0.0)
                for row in rows
            }
        except duckdb.Error:
            best_week_by_player = {}

        snapshots: dict[str, CurrentStrengthSnapshot] = {}
        for inputs in all_inputs.values():
            for player_id in inputs.starters + inputs.bench + inputs.ir + inputs.taxi:
                if (
                    not player_id
                    or player_id in snapshots
                    or player_id not in inputs.weekly_fantasy_pts
                ):
                    continue
                ppg = float(inputs.weekly_fantasy_pts[player_id])
                games_played = int(inputs.player_games_played.get(player_id, 0) or 0)
                role_stability = _clamp01(games_played / 17.0) if games_played else 0.45
                current_production = _clamp01(ppg / 25.0)
                short_term = _clamp01(0.7 * current_production + 0.3 * role_stability)
                best_week = best_week_by_player.get(player_id, ppg)
                ceiling = _clamp01(best_week / 30.0)
                floor = _clamp01((ppg / 20.0) * max(role_stability, 0.5))
                snapshots[player_id] = CurrentStrengthSnapshot(
                    current_production=current_production,
                    short_term=short_term,
                    ceiling=ceiling,
                    floor=floor,
                )
        return snapshots

    def _value_proxy(
        self,
        inputs: ScorecardInputs,
        player_id: str,
        strength_snapshots: dict[str, CurrentStrengthSnapshot] | None = None,
    ) -> float:
        base_value = self._base_current_strength_value(inputs, player_id)
        if player_id not in inputs.weekly_fantasy_pts or not strength_snapshots:
            return base_value

        snapshot = strength_snapshots.get(player_id)
        if snapshot is None:
            return base_value

        supportive_cluster = (
            LINEUP_CURRENT_STRENGTH_CEILING_WEIGHT * snapshot.ceiling
            + LINEUP_CURRENT_STRENGTH_SHORT_TERM_WEIGHT
            * max(snapshot.short_term, snapshot.current_production)
            + LINEUP_CURRENT_STRENGTH_FLOOR_WEIGHT
            * max(snapshot.floor, snapshot.current_production)
        )
        adjustment = max(
            LINEUP_CURRENT_STRENGTH_MIN_ADJUSTMENT,
            min(
                LINEUP_CURRENT_STRENGTH_MAX_ADJUSTMENT,
                (supportive_cluster - snapshot.current_production)
                * LINEUP_CURRENT_STRENGTH_ADJUSTMENT_MULTIPLIER,
            ),
        )
        return max(0.0, base_value + adjustment)

    def _iter_active_slots(self, inputs: ScorecardInputs) -> list[tuple[str, str, int]]:
        out: list[tuple[str, str, int]] = []
        for i, slot in enumerate(inputs.roster_positions):
            if _slot_skip(slot):
                continue
            if i >= len(inputs.starters):
                break
            pid = inputs.starters[i]
            if not pid:
                continue
            out.append((slot, str(pid), i))
        return out

    def _compute_replacement_level(
        self,
        all_inputs: dict[int, ScorecardInputs],
        slot_label: str,
        *,
        flex_pool: bool,
        strength_snapshots: dict[str, CurrentStrengthSnapshot] | None = None,
    ) -> float:
        first_in = next(iter(all_inputs.values()))
        med_avg = float(
            sum(first_in.position_medians.values())
            / max(len(first_in.position_medians), 1)
        )

        values: list[float] = []
        if flex_pool:
            for inputs in all_inputs.values():
                for slot, pid, _ in self._iter_active_slots(inputs):
                    if _flex_like(slot):
                        values.append(self._value_proxy(inputs, pid, strength_snapshots))
        else:
            target = slot_label.strip().upper()
            for inputs in all_inputs.values():
                for slot, pid, _ in self._iter_active_slots(inputs):
                    if _flex_like(slot):
                        continue
                    if slot.strip().upper() == target:
                        values.append(self._value_proxy(inputs, pid, strength_snapshots))

        if not values:
            return float(first_in.position_medians.get(slot_label, med_avg))
        return _median(values)

    def _title_window_composites(
        self,
        roster_ids: list[int],
        ceiling_norm: dict[int, float],
        stability_norm: dict[int, float],
        depth_norm: dict[int, float],
    ) -> dict[int, float]:
        return {
            roster_id: (
                TITLE_WINDOW_WEIGHTS["ceiling"] * ceiling_norm.get(roster_id, 0.0)
                + TITLE_WINDOW_WEIGHTS["stability"] * stability_norm.get(roster_id, 0.0)
                + TITLE_WINDOW_WEIGHTS["depth"] * depth_norm.get(roster_id, 0.0)
            )
            for roster_id in roster_ids
        }

    def _benchmark_pool_ids(self, title_window_composites: dict[int, float]) -> set[int]:
        if not title_window_composites:
            return set()
        sorted_ids = sorted(
            title_window_composites,
            key=lambda roster_id: float(title_window_composites[roster_id]),
            reverse=True,
        )
        cutoff = max(2, math.ceil(len(sorted_ids) * LINEUP_TARGET_POOL_FRACTION))
        top_ids = sorted_ids[:cutoff]
        in_window_ids = [
            roster_id
            for roster_id in top_ids
            if title_window_composites[roster_id] >= FADING_WINDOW_THRESHOLD
        ]
        return set(in_window_ids or top_ids)

    def _build_target_triplet(
        self,
        values: list[float],
        fallback: float,
    ) -> tuple[float, float, float]:
        playoff = max(fallback, float(_percentile(values, PLAYOFF_TARGET_PERCENTILE) or fallback))
        title = max(playoff, float(_percentile(values, TITLE_TARGET_PERCENTILE) or playoff))
        elite = max(title, float(_percentile(values, ELITE_TARGET_PERCENTILE) or title))
        return playoff, title, elite

    def _compute_benchmark_targets(
        self,
        all_inputs: dict[int, ScorecardInputs],
        benchmark_pool_ids: set[int],
        slot_label: str,
        *,
        flex_pool: bool,
        strength_snapshots: dict[str, CurrentStrengthSnapshot] | None = None,
    ) -> SlotBenchmarkTargets:
        fallback = self._compute_replacement_level(
            all_inputs,
            slot_label,
            flex_pool=flex_pool,
            strength_snapshots=strength_snapshots,
        )
        target = slot_label.strip().upper()
        contender_values: list[float] = []
        all_values: list[float] = []
        for roster_id, inputs in all_inputs.items():
            for slot, pid, _ in self._iter_active_slots(inputs):
                if flex_pool:
                    if not _flex_like(slot):
                        continue
                else:
                    if _flex_like(slot) or slot.strip().upper() != target:
                        continue

                value = self._value_proxy(inputs, pid, strength_snapshots)
                all_values.append(value)
                if roster_id in benchmark_pool_ids:
                    contender_values.append(value)

        if len(contender_values) >= 2:
            playoff, title, elite = self._build_target_triplet(contender_values, fallback)
            return SlotBenchmarkTargets(
                playoff_target=playoff,
                title_target=title,
                elite_target=elite,
                benchmark_used=True,
                benchmark_source="benchmark_pool",
                benchmark_sample_size=len(contender_values),
            )

        top_tier_values = _top_tier_values(all_values)
        if len(top_tier_values) >= 2:
            playoff, title, elite = self._build_target_triplet(top_tier_values, fallback)
            return SlotBenchmarkTargets(
                playoff_target=playoff,
                title_target=title,
                elite_target=elite,
                benchmark_used=True,
                benchmark_source="top_tier_fallback",
                benchmark_sample_size=len(top_tier_values),
            )

        if contender_values:
            playoff, title, elite = self._build_target_triplet(contender_values, fallback)
            return SlotBenchmarkTargets(
                playoff_target=playoff,
                title_target=title,
                elite_target=elite,
                benchmark_used=True,
                benchmark_source="single_roster_fallback",
                benchmark_sample_size=len(contender_values),
            )

        return SlotBenchmarkTargets(
            playoff_target=fallback,
            title_target=fallback,
            elite_target=fallback,
            benchmark_used=False,
            benchmark_source="replacement_level",
            benchmark_sample_size=0,
        )

    def _compute_overall_benchmark_targets(
        self,
        total_scores: dict[int, float],
        benchmark_pool_ids: set[int],
    ) -> SlotBenchmarkTargets:
        all_values = list(total_scores.values())
        fallback = _median(all_values) if all_values else 0.0
        contender_values = [
            total_scores[roster_id]
            for roster_id in benchmark_pool_ids
            if roster_id in total_scores
        ]

        if len(contender_values) >= 2:
            playoff, title, elite = self._build_target_triplet(contender_values, fallback)
            return SlotBenchmarkTargets(
                playoff_target=playoff,
                title_target=title,
                elite_target=elite,
                benchmark_used=True,
                benchmark_source="benchmark_pool",
                benchmark_sample_size=len(contender_values),
            )

        top_tier_values = _top_tier_values(all_values)
        if len(top_tier_values) >= 2:
            playoff, title, elite = self._build_target_triplet(top_tier_values, fallback)
            return SlotBenchmarkTargets(
                playoff_target=playoff,
                title_target=title,
                elite_target=elite,
                benchmark_used=True,
                benchmark_source="top_tier_fallback",
                benchmark_sample_size=len(top_tier_values),
            )

        return SlotBenchmarkTargets(
            playoff_target=fallback,
            title_target=fallback,
            elite_target=fallback,
            benchmark_used=False,
            benchmark_source="league_median_fallback",
            benchmark_sample_size=len(all_values),
        )

    def _detect_context_flags(
        self, league_id: str, player_id: str, inputs: ScorecardInputs
    ) -> list[str]:
        flags: list[str] = []
        position = inputs.player_positions.get(player_id, "UNKNOWN").upper()
        age = inputs.player_ages.get(player_id)
        cliff_age = POSITIONAL_CLIFF_AGE.get(position)
        if age is not None and cliff_age is not None:
            if age >= cliff_age - AGE_CLIFF_PROXIMITY_SEASONS:
                flags.append("age_cliff_proximity")

        games_played = inputs.player_games_played.get(player_id)
        if player_id in inputs.starters and games_played is not None and games_played < 8:
            flags.append("injury_recovery")

        try:
            rows = self._conn.execute(
                """
                SELECT flag
                FROM player_context_overrides
                WHERE league_id = ? AND player_id = ?
                """,
                [league_id, player_id],
            ).fetchall()
        except duckdb.Error:
            rows = []

        for row in rows:
            flag = str(row[0] or "")
            if flag in _VALID_CONTEXT_FLAGS and flag not in flags:
                flags.append(flag)

        return [
            flag for flag in _VALID_CONTEXT_FLAGS if flag in flags
        ]

    def compute_all(
        self,
        league_id: str,
        all_inputs: dict[int, ScorecardInputs],
        scorecards: dict[int, TeamScorecard] | None = None,
    ) -> dict[int, LineupResult]:
        if not all_inputs:
            return {}

        roster_ids = list(all_inputs.keys())
        strength_snapshots = self._load_current_strength_snapshots(all_inputs)

        ceiling_raw: dict[int, float] = {}
        stability_raw: dict[int, float] = {}
        depth_raw: dict[int, float] = {}
        for roster_id, inputs in all_inputs.items():
            starters_set = set(inputs.starters)
            ceiling_raw[roster_id] = float(
                self._ceiling_score_raw(
                    league_id,
                    roster_id,
                    inputs,
                    starters_set,
                    strength_snapshots,
                )
            )
            if scorecards and roster_id in scorecards:
                fragility = float(scorecards[roster_id].fragility)
                stability_raw[roster_id] = max(0.0, min(1.0, 1.0 - fragility))
            else:
                stability_raw[roster_id] = 0.5

            bench_vals = [
                self._value_proxy(inputs, pid, strength_snapshots)
                for pid in inputs.bench
            ]
            med_avg = float(
                sum(inputs.position_medians.values())
                / max(len(inputs.position_medians), 1)
            )
            depth_raw[roster_id] = float(sum(1 for value in bench_vals if value >= med_avg))

        ceiling_norm = normalize_within_league(ceiling_raw)
        stability_norm = normalize_within_league(stability_raw)
        depth_norm = normalize_within_league(depth_raw)
        title_window_composites = self._title_window_composites(
            roster_ids,
            ceiling_norm,
            stability_norm,
            depth_norm,
        )
        benchmark_pool_ids = self._benchmark_pool_ids(title_window_composites)

        position_keys: set[str] = set()
        for inputs in all_inputs.values():
            for slot, _pid, _ in self._iter_active_slots(inputs):
                if not _flex_like(slot):
                    position_keys.add(slot.strip().upper())

        repl_by_pos: dict[str, float] = {}
        benchmark_targets_by_pos: dict[str, SlotBenchmarkTargets] = {}
        for position_key in position_keys:
            repl_by_pos[position_key] = self._compute_replacement_level(
                all_inputs,
                position_key,
                flex_pool=False,
                strength_snapshots=strength_snapshots,
            )
            benchmark_targets_by_pos[position_key] = self._compute_benchmark_targets(
                all_inputs,
                benchmark_pool_ids,
                position_key,
                flex_pool=False,
                strength_snapshots=strength_snapshots,
            )

        flex_replacement = self._compute_replacement_level(
            all_inputs,
            "",
            flex_pool=True,
            strength_snapshots=strength_snapshots,
        )
        flex_targets = self._compute_benchmark_targets(
            all_inputs,
            benchmark_pool_ids,
            "",
            flex_pool=True,
            strength_snapshots=strength_snapshots,
        )
        contender_benchmark_used_any = flex_targets.benchmark_used or any(
            targets.benchmark_used for targets in benchmark_targets_by_pos.values()
        )

        max_slots = max(
            (len(self._iter_active_slots(inputs)) for inputs in all_inputs.values()),
            default=0,
        )
        raw_by_slot: list[dict[int, float]] = [{} for _ in range(max_slots)]
        slot_meta: dict[int, dict[int, tuple[str, str, str, float, float]]] = {
            roster_id: {} for roster_id in roster_ids
        }

        for roster_id, inputs in all_inputs.items():
            med_avg = float(
                sum(inputs.position_medians.values())
                / max(len(inputs.position_medians), 1)
            )
            for slot_index, (slot, pid, _orig_idx) in enumerate(self._iter_active_slots(inputs)):
                starter_value = self._value_proxy(inputs, pid, strength_snapshots)
                player_position = inputs.player_positions.get(pid, slot).upper()
                if _flex_like(slot):
                    replacement_level = flex_replacement
                else:
                    replacement_level = repl_by_pos.get(
                        slot.strip().upper(),
                        float(inputs.position_medians.get(player_position, med_avg)),
                    )
                raw_by_slot[slot_index][roster_id] = max(0.0, starter_value - replacement_level)
                slot_meta[roster_id][slot_index] = (
                    slot,
                    pid,
                    player_position,
                    starter_value,
                    replacement_level,
                )

        norm_by_slot = [normalize_within_league(raw) if raw else {} for raw in raw_by_slot]
        total_lineup_scores = {
            roster_id: float(sum(raw.get(roster_id, 0.0) for raw in norm_by_slot))
            for roster_id in roster_ids
        }
        overall_targets = self._compute_overall_benchmark_targets(
            total_lineup_scores,
            benchmark_pool_ids,
        )

        results: dict[int, LineupResult] = {}
        now = datetime.now(timezone.utc).isoformat()

        for roster_id, inputs in all_inputs.items():
            slot_scores: list[LineupSlotScore] = []
            total_lineup_score = float(total_lineup_scores.get(roster_id, 0.0))
            guard_active = bool(
                scorecards
                and roster_id in scorecards
                and float(scorecards[roster_id].positional_insulation) >= ELITE_INSULATION_THRESHOLD
            )

            for slot_index in range(max_slots):
                if slot_index not in slot_meta[roster_id]:
                    continue
                slot, pid, position, starter_value, replacement_level = slot_meta[roster_id][
                    slot_index
                ]
                benchmark_targets = (
                    flex_targets
                    if _flex_like(slot)
                    else benchmark_targets_by_pos.get(
                        slot.strip().upper(),
                        SlotBenchmarkTargets(
                            playoff_target=float(replacement_level),
                            title_target=float(replacement_level),
                            elite_target=float(replacement_level),
                            benchmark_used=False,
                            benchmark_source="replacement_level",
                            benchmark_sample_size=0,
                        ),
                    )
                )
                contender_benchmark = benchmark_targets.title_target
                weak_by_median = starter_value < replacement_level
                below_playoff_target = starter_value < benchmark_targets.playoff_target
                below_title_target = starter_value < benchmark_targets.title_target
                below_elite_target = starter_value < benchmark_targets.elite_target
                weak_relative_to_contender = below_title_target
                gap_to_playoff_target = max(0.0, benchmark_targets.playoff_target - starter_value)
                gap_to_title_target = max(0.0, benchmark_targets.title_target - starter_value)
                gap_to_elite_target = max(0.0, benchmark_targets.elite_target - starter_value)
                upgrade_leverage_score = gap_to_title_target
                format_urgency_weight = (
                    TE_NON_PREMIUM_URGENCY_WEIGHT
                    if position == "TE" and not _te_premium_active(inputs)
                    else 1.0
                )
                score = float(norm_by_slot[slot_index].get(roster_id, 0.0))
                slot_scores.append(
                    LineupSlotScore(
                        position=position,
                        player_id=pid,
                        player_name=_player_display(self._conn, pid),
                        starter_value=float(starter_value),
                        replacement_level=float(replacement_level),
                        score=score,
                        contender_benchmark=float(contender_benchmark),
                        playoff_target=float(benchmark_targets.playoff_target),
                        title_target=float(benchmark_targets.title_target),
                        elite_target=float(benchmark_targets.elite_target),
                        upgrade_leverage_score=float(upgrade_leverage_score),
                        gap_to_playoff_target=float(gap_to_playoff_target),
                        gap_to_title_target=float(gap_to_title_target),
                        gap_to_elite_target=float(gap_to_elite_target),
                        weak_by_median=weak_by_median,
                        below_playoff_target=below_playoff_target,
                        below_title_target=below_title_target,
                        below_elite_target=below_elite_target,
                        weak_relative_to_contender=weak_relative_to_contender,
                        benchmark_used=benchmark_targets.benchmark_used,
                        benchmark_source=benchmark_targets.benchmark_source,
                        benchmark_sample_size=benchmark_targets.benchmark_sample_size,
                        elite_insulation_guard=guard_active,
                        format_urgency_weight=float(format_urgency_weight),
                        player_context_flags=self._detect_context_flags(league_id, pid, inputs),
                    )
                )

            best_slot = max(
                slot_scores,
                key=lambda slot: (
                    slot.upgrade_leverage_score * slot.format_urgency_weight,
                    slot.upgrade_leverage_score,
                    slot.score,
                ),
                default=None,
            )
            weighted_leverage = (
                best_slot.upgrade_leverage_score * best_slot.format_urgency_weight
                if best_slot
                else 0.0
            )

            composite = title_window_composites.get(roster_id, 0.0)

            if composite >= PEAK_WINDOW_THRESHOLD:
                label = "Peak Window"
            elif composite >= FADING_WINDOW_THRESHOLD:
                label = "Fading Window"
            else:
                label = "Outside Window"

            results[roster_id] = LineupResult(
                league_id=league_id,
                roster_id=roster_id,
                computed_at=now,
                slot_scores=slot_scores,
                total_lineup_score=float(total_lineup_score),
                overall_playoff_target=float(overall_targets.playoff_target),
                overall_title_target=float(overall_targets.title_target),
                overall_elite_target=float(overall_targets.elite_target),
                overall_gap_to_playoff_target=float(
                    max(0.0, overall_targets.playoff_target - total_lineup_score)
                ),
                overall_gap_to_title_target=float(
                    max(0.0, overall_targets.title_target - total_lineup_score)
                ),
                overall_gap_to_elite_target=float(
                    max(0.0, overall_targets.elite_target - total_lineup_score)
                ),
                overall_benchmark_source=overall_targets.benchmark_source,
                overall_benchmark_sample_size=overall_targets.benchmark_sample_size,
                title_window_label=label,
                title_window_composite=float(composite),
                ceiling_score=float(ceiling_norm.get(roster_id, 0.0)),
                stability_score=float(stability_norm.get(roster_id, 0.0)),
                depth_score=float(depth_norm.get(roster_id, 0.0)),
                contender_benchmark_used=contender_benchmark_used_any,
                upgrade_leverage_point=(
                    f"{best_slot.player_name} ({best_slot.position})"
                    if best_slot
                    else ""
                ),
                upgrade_title_equity_delta=float(
                    min(1.0, weighted_leverage * UPGRADE_LEVERAGE_BASE_EQUITY)
                ),
            )

        return results

    def _ceiling_score_raw(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        starters: set[str],
        strength_snapshots: dict[str, CurrentStrengthSnapshot] | None = None,
    ) -> float:
        if not starters:
            return 0.0
        placeholders = ",".join(["?"] * len(starters))
        try:
            row = self._conn.execute(
                f"""
                SELECT MAX(comp_ceiling)
                FROM player_values
                WHERE league_id = ? AND roster_id = ? AND player_id IN ({placeholders})
                """,
                [league_id, roster_id, *list(starters)],
            ).fetchone()
            if row and row[0] is not None:
                return float(row[0])
        except duckdb.Error:
            pass
        return max(
            (self._value_proxy(inputs, pid, strength_snapshots) for pid in inputs.starters if pid),
            default=0.0,
        )

    def attach_recommendation_cards(self, result: LineupResult) -> LineupResult:
        result.recommendation_cards = self._card_engine.build_lineup_cards(result)
        return result
