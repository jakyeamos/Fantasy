from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from fantasy.intelligence.constants import POSITIONAL_CLIFF_AGE
from fantasy.intelligence.models import ScorecardInputs
from fantasy.lineup.constants import (
    AGE_CLIFF_PROXIMITY_SEASONS,
    CUT_VALUE_FLOOR,
    HYGIENE_MAX_SUGGESTIONS_PER_TYPE,
    STASH_AGE_CEILING,
    STASH_CEILING_FLOOR,
)
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import HygieneResult, HygieneSuggestion
from fantasy.recommendation.card_engine import RecommendationCardEngine
from fantasy.trade.models import TradeAsset, TradeRequest
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.trade_engine import TradeEngine

_MIN_EXPLOITABILITY_SCORE = 40.0
_MIN_TRADE_EVIDENCE = 10
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


def _loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return dict(json.loads(raw))
    except json.JSONDecodeError:
        return {}


class HygieneEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = LineupRepo(conn)
        self._trade_engine = TradeEngine(conn)
        self._package_builder = PackageBuilder(conn)
        self._card_engine = RecommendationCardEngine(conn)

    def compute(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        direction_label: str,
        all_inputs: dict[int, ScorecardInputs],
    ) -> HygieneResult:
        consolidate = self._consolidation_suggestions(
            league_id, roster_id, inputs, all_inputs, direction_label
        )
        cut = self._cut_suggestions(league_id, roster_id, inputs)
        package = self._package_suggestions(
            league_id, roster_id, inputs, all_inputs, direction_label
        )
        throw_in = self._throw_in_now_suggestions(
            league_id, roster_id, inputs, all_inputs
        )
        shop = self._shop_suggestions(league_id, roster_id, inputs)
        hold = self._hold_suggestions(league_id, roster_id, inputs)
        stash = self._stash_suggestions(league_id, roster_id, inputs)
        taxi = self._taxi_suggestions(league_id, roster_id, inputs)
        handcuff = self._handcuff_speculative_suggestions(
            league_id, roster_id, inputs
        )
        reroll = self._reroll_into_pick_suggestions(league_id, roster_id, inputs)

        ordered = (
            consolidate
            + cut
            + package
            + throw_in
            + shop
            + hold
            + stash
            + taxi
            + handcuff
            + reroll
        )
        ordered = self._apply_coverage_guarantee(
            league_id, roster_id, inputs, all_inputs, ordered
        )
        now = datetime.now(timezone.utc).isoformat()
        result = HygieneResult(
            league_id=league_id,
            roster_id=roster_id,
            computed_at=now,
            suggestions=ordered,
        )
        result.recommendation_cards = self._card_engine.build_hygiene_cards(
            result.suggestions,
            league_id,
        )
        return result

    def _bench_players(self, inputs: ScorecardInputs) -> list[str]:
        excluded = set(inputs.starters) | set(inputs.ir) | set(inputs.taxi)
        return [player_id for player_id in inputs.bench if player_id not in excluded]

    def _roster_players(self, inputs: ScorecardInputs) -> list[str]:
        excluded = set(inputs.ir) | set(inputs.taxi)
        return [
            player_id
            for player_id in inputs.starters + inputs.bench
            if player_id not in excluded
        ]

    def _player_metrics(
        self, league_id: str, roster_id: int, player_ids: list[str]
    ) -> dict[str, dict[str, float]]:
        if not player_ids:
            return {}
        rows = self._conn.execute(
            """
            SELECT player_id, lens_direction, comp_ceiling
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND player_id IN (
                SELECT UNNEST(?)
            )
            """,
            [league_id, roster_id, player_ids],
        ).fetchall()
        metrics: dict[str, dict[str, float]] = {}
        for player_id, lens_direction, comp_ceiling in rows:
            metrics[str(player_id)] = {
                "lens_direction": float(lens_direction or 0.0),
                "comp_ceiling": float(comp_ceiling or 0.0),
            }
        return metrics

    def _transaction_count(self, player_id: str, league_id: str) -> int:
        rows = self._conn.execute(
            """
            SELECT adds, drops
            FROM transactions
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        count = 0
        for adds, drops in rows:
            for payload in (adds, drops):
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if player_id in data:
                    count += 1
        return count

    def _context_flags_for(
        self, player_id: str, league_id: str, inputs: ScorecardInputs
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

    def _combined_context_flags(
        self, player_ids: list[str], league_id: str, inputs: ScorecardInputs
    ) -> list[str]:
        flags: list[str] = []
        for player_id in player_ids:
            for flag in self._context_flags_for(player_id, league_id, inputs):
                if flag not in flags:
                    flags.append(flag)
        return flags

    def _with_context_reasoning(self, reasoning: str, flags: list[str]) -> str:
        if "injury_recovery" in flags and "injury" not in reasoning.lower():
            return (
                f"{reasoning} Player is recovering from injury - confirm availability "
                "before acting."
            )
        return reasoning

    def _suggestion(
        self,
        *,
        action_type: str,
        league_id: str,
        inputs: ScorecardInputs,
        primary_player_ids: list[str],
        primary_player_names: list[str],
        reasoning: str,
        direction_fit_score: float,
        timing_rationale: str,
        target_player_id: str | None = None,
        target_player_name: str | None = None,
        counterparty_roster_id: int | None = None,
        counterparty_name: str | None = None,
        packaging_rationale: str | None = None,
    ) -> HygieneSuggestion:
        context_flags = self._combined_context_flags(
            primary_player_ids, league_id, inputs
        )
        return HygieneSuggestion(
            action_type=action_type,
            primary_player_ids=primary_player_ids,
            primary_player_names=primary_player_names,
            target_player_id=target_player_id,
            target_player_name=target_player_name,
            counterparty_roster_id=counterparty_roster_id,
            counterparty_name=counterparty_name,
            reasoning=self._with_context_reasoning(reasoning, context_flags),
            direction_fit_score=direction_fit_score,
            timing_rationale=timing_rationale,
            packaging_rationale=packaging_rationale,
            player_context_flags=context_flags,
        )

    def _player_name(self, player_id: str) -> str:
        row = self._conn.execute(
            "SELECT COALESCE(full_name, player_id) FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        return str(row[0]) if row else player_id

    def _row_lens(self, league_id: str, roster_id: int, player_id: str) -> float:
        row = self._conn.execute(
            """
            SELECT lens_direction
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND player_id = ?
            """,
            [league_id, roster_id, player_id],
        ).fetchone()
        return float(row[0] or 0.0) if row is not None else 0.0

    def _find_upgrade_target(
        self,
        league_id: str,
        roster_id: int,
        all_inputs: dict[int, ScorecardInputs],
    ) -> tuple[str | None, int | None, str | None]:
        name_rows = self._conn.execute(
            """
            SELECT roster_id, owner_display_name
            FROM rosters
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        name_by_roster = {
            int(roster): str(name or f"Manager {roster}")
            for roster, name in name_rows
        }

        for other_roster_id, other_inputs in all_inputs.items():
            if other_roster_id == roster_id:
                continue
            profile = self._conn.execute(
                """
                SELECT exploitability_score, evidence_count, low_confidence
                FROM manager_profiles
                WHERE league_id = ? AND roster_id = ?
                LIMIT 1
                """,
                [league_id, other_roster_id],
            ).fetchone()
            if profile is None:
                continue
            exploitability_score = float(profile[0] or 0.0)
            evidence_count = int(profile[1] or 0)
            low_confidence = bool(profile[2])
            if low_confidence:
                continue
            if evidence_count < _MIN_TRADE_EVIDENCE:
                continue
            if exploitability_score < _MIN_EXPLOITABILITY_SCORE:
                continue

            for player_id in other_inputs.starters + other_inputs.bench:
                if self._row_lens(league_id, other_roster_id, player_id) >= 0.5:
                    return (
                        player_id,
                        other_roster_id,
                        name_by_roster.get(other_roster_id, "Manager"),
                    )
        return None, None, None

    def _cut_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        candidates = sorted(
            (
                (player_id, values["lens_direction"])
                for player_id, values in metrics.items()
                if values["lens_direction"] < CUT_VALUE_FLOOR
            ),
            key=lambda item: item[1],
        )

        suggestions: list[HygieneSuggestion] = []
        for player_id, lens in candidates[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]:
            trade_count = self._transaction_count(player_id, league_id)
            if lens >= 0.4 and trade_count == 0:
                continue
            player_name = self._player_name(player_id)
            suggestions.append(
                self._suggestion(
                    action_type="cut",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Cutting {player_name} frees a roster spot for a better waiver target. "
                        f"Dynasty value is minimal ({lens:.2f} directional fit)."
                    ),
                    direction_fit_score=max(0.0, min(1.0, 1.0 - lens)),
                    timing_rationale=(
                        "Cut now to free the roster spot before the next waiver cycle."
                    ),
                )
            )
        return suggestions

    def _stash_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        suggestions: list[HygieneSuggestion] = []
        for player_id in bench:
            values = metrics.get(player_id)
            if values is None:
                continue
            age = int(inputs.player_ages.get(player_id, 99))
            ceiling = float(values["comp_ceiling"])
            if age > STASH_AGE_CEILING or ceiling < STASH_CEILING_FLOOR:
                continue
            player_name = self._player_name(player_id)
            suggestions.append(
                self._suggestion(
                    action_type="stash",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Hold {player_name} as a stash - young asset (age {age}) with "
                        f"ceiling upside ({ceiling:.2f})."
                    ),
                    direction_fit_score=0.7,
                    timing_rationale=(
                        "Stash through the next development window while the ceiling outcome "
                        "still justifies the bench spot."
                    ),
                )
            )
        return suggestions[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]

    def _taxi_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        config = self._repo.get_taxi_config(league_id)
        if config is None:
            return []

        occupancy = self._repo.get_slot_occupancy(league_id, roster_id)
        if occupancy.get("taxi_total", 0) <= 0:
            return []
        if occupancy.get("taxi_used", 0) >= occupancy.get("taxi_total", 0):
            return []

        bench = self._bench_players(inputs)
        season = int(inputs.season)
        suggestions: list[HygieneSuggestion] = []
        for player_id in bench:
            years_pro = self._years_pro(player_id, season, inputs)
            manual_exception = player_id in config.manual_exceptions
            eligible = manual_exception or years_pro <= config.years_pro_cutoff
            if not eligible:
                continue
            player_name = self._player_name(player_id)
            reason_tail = (
                "manual exception override applies."
                if manual_exception
                else f"eligible ({years_pro} {'years' if years_pro != 1 else 'year'} pro)."
            )
            suggestions.append(
                self._suggestion(
                    action_type="taxi",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Move {player_name} to taxi - {reason_tail} "
                        "This frees a live bench spot."
                    ),
                    direction_fit_score=0.6,
                    timing_rationale=(
                        "Move now while a taxi slot is open so the bench spot can be reused "
                        "for active churn."
                    ),
                )
            )
        return suggestions[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]

    def _hold_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        candidates = sorted(
            (
                (player_id, values["lens_direction"])
                for player_id, values in metrics.items()
                if values["lens_direction"] >= 0.4
                and self._transaction_count(player_id, league_id) == 0
            ),
            key=lambda item: item[1],
            reverse=True,
        )

        suggestions: list[HygieneSuggestion] = []
        for player_id, lens in candidates[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]:
            player_name = self._player_name(player_id)
            suggestions.append(
                self._suggestion(
                    action_type="hold",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Hold despite weak market on {player_name} - the player still carries "
                        f"useful production value ({lens:.2f}) even though no buyer is showing."
                    ),
                    direction_fit_score=min(1.0, max(0.4, lens)),
                    timing_rationale=(
                        "Hold until a buyer surfaces; this player has value but near-zero "
                        "current market activity."
                    ),
                )
            )
        return suggestions

    def _shop_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        roster_players = self._roster_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, roster_players)
        suggestions: list[HygieneSuggestion] = []

        for player_id in roster_players:
            values = metrics.get(player_id)
            if values is None:
                continue
            lens = float(values["lens_direction"])
            trade_count = self._transaction_count(player_id, league_id)
            if lens >= 0.4 and trade_count == 0:
                continue

            position = inputs.player_positions.get(player_id, "UNKNOWN").upper()
            age = int(inputs.player_ages.get(player_id, 24))
            cliff_age = POSITIONAL_CLIFF_AGE.get(position, 30)
            adp_rank = inputs.adp_ranks.get(player_id)
            is_liquid = (adp_rank is not None and adp_rank <= 60) or (
                lens >= 0.6 and age > cliff_age - 3
            )
            if not is_liquid:
                continue

            player_name = self._player_name(player_id)
            suggestions.append(
                self._suggestion(
                    action_type="shop",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Shop {player_name} now - the market still treats this as a liquid "
                        "asset, which makes it easier to turn into a cleaner fit."
                    ),
                    direction_fit_score=min(1.0, max(0.45, lens)),
                    timing_rationale=(
                        "Shop now - market value is at or near peak; holding longer risks "
                        "value decay."
                    ),
                )
            )

        suggestions.sort(key=lambda suggestion: suggestion.direction_fit_score, reverse=True)
        return suggestions[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]

    def _package_suggestions(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        all_inputs: dict[int, ScorecardInputs],
        _direction_label: str,
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        candidates = [
            player_id
            for player_id in bench
            if 0.2 <= float(metrics.get(player_id, {}).get("lens_direction", 0.0)) <= 0.45
        ]
        if len(candidates) < 2:
            return []

        first, second = candidates[:2]
        first_name = self._player_name(first)
        second_name = self._player_name(second)
        target_player_id, target_roster_id, counterparty_name = self._find_upgrade_target(
            league_id, roster_id, all_inputs
        )
        target_player_name = (
            self._player_name(target_player_id) if target_player_id else None
        )

        return [
            self._suggestion(
                action_type="package",
                league_id=league_id,
                inputs=inputs,
                primary_player_ids=[first, second],
                primary_player_names=[first_name, second_name],
                target_player_id=target_player_id,
                target_player_name=target_player_name,
                counterparty_roster_id=target_roster_id,
                counterparty_name=counterparty_name,
                reasoning=(
                    f"Package {first_name} + {second_name} to chase a cleaner upgrade path. "
                    "Neither profile wins enough value as a standalone shop piece."
                ),
                direction_fit_score=0.62,
                timing_rationale=(
                    "Package when you have an upgrade target identified; holding as a standalone "
                    "asset has diminishing returns."
                ),
                packaging_rationale=(
                    f"More useful as a 2-for-1 sweetener than a standalone sell - package with "
                    f"{second_name if first_name != second_name else first_name} to unlock an upgrade."
                ),
            )
        ]

    def _throw_in_now_suggestions(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        all_inputs: dict[int, ScorecardInputs],
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        candidates = [
            player_id
            for player_id in bench
            if 0.15 <= float(metrics.get(player_id, {}).get("lens_direction", 0.0)) <= 0.30
        ]
        if not candidates:
            return []

        player_id = candidates[0]
        player_name = self._player_name(player_id)
        target_player_id, target_roster_id, counterparty_name = self._find_upgrade_target(
            league_id, roster_id, all_inputs
        )

        return [
            self._suggestion(
                action_type="throw_in_now",
                league_id=league_id,
                inputs=inputs,
                primary_player_ids=[player_id],
                primary_player_names=[player_name],
                target_player_id=target_player_id,
                target_player_name=(
                    self._player_name(target_player_id) if target_player_id else None
                ),
                counterparty_roster_id=target_roster_id,
                counterparty_name=counterparty_name,
                reasoning=(
                    f"Use {player_name} as the throw-in now before the asset loses even the "
                    "small sweetener value it still carries."
                ),
                direction_fit_score=0.52,
                timing_rationale=(
                    "Use now before value erodes further; do not hold waiting for a standalone offer."
                ),
                packaging_rationale=(
                    "Include as a throw-in to sweeten an existing trade offer - standalone value is "
                    "low, but as an add-on this player can tip a deal."
                ),
            )
        ]

    def _handcuff_speculative_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        starter_names = {player_id: self._player_name(player_id) for player_id in inputs.starters}
        suggestions: list[HygieneSuggestion] = []

        for player_id in bench:
            player_position = inputs.player_positions.get(player_id, "UNKNOWN")
            fragile_starter = next(
                (
                    starter_id
                    for starter_id in inputs.starters
                    if inputs.player_positions.get(starter_id, "UNKNOWN") == player_position
                    and inputs.player_games_played.get(starter_id, 17) < 10
                ),
                None,
            )
            if fragile_starter is None:
                continue
            player_name = self._player_name(player_id)
            starter_name = starter_names.get(fragile_starter, fragile_starter)
            suggestions.append(
                self._suggestion(
                    action_type="handcuff_speculative",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Keep {player_name} as a speculative handcuff because {starter_name} "
                        "still carries real availability risk."
                    ),
                    direction_fit_score=0.58,
                    timing_rationale=(
                        f"Keep while {starter_name} is a fragility risk; re-evaluate after a "
                        "healthy full season."
                    ),
                )
            )
        return suggestions[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]

    def _reroll_into_pick_suggestions(
        self, league_id: str, roster_id: int, inputs: ScorecardInputs
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        candidates = sorted(
            (
                (player_id, values["lens_direction"])
                for player_id, values in metrics.items()
                if CUT_VALUE_FLOOR > values["lens_direction"] > 0.05
            ),
            key=lambda item: item[1],
        )

        suggestions: list[HygieneSuggestion] = []
        for player_id, lens in candidates[:HYGIENE_MAX_SUGGESTIONS_PER_TYPE]:
            player_name = self._player_name(player_id)
            suggestions.append(
                self._suggestion(
                    action_type="reroll_into_pick",
                    league_id=league_id,
                    inputs=inputs,
                    primary_player_ids=[player_id],
                    primary_player_names=[player_name],
                    reasoning=(
                        f"Reroll {player_name} into a late pick if possible - there is still "
                        f"a trace amount of market value ({lens:.2f}) to convert."
                    ),
                    direction_fit_score=0.5,
                    timing_rationale=(
                        "Ask for a late pick as the price to release this player rather than "
                        "cutting outright; any return beats zero."
                    ),
                )
            )
        return suggestions

    def _consolidation_suggestions(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        all_inputs: dict[int, ScorecardInputs],
        _direction_label: str,
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        metrics = self._player_metrics(league_id, roster_id, bench)
        in_scope = sorted(
            (
                player_id
                for player_id in bench
                if player_id in metrics
            ),
            key=lambda player_id: float(metrics[player_id]["lens_direction"]),
        )
        if len(in_scope) < 2:
            return []

        first, second = in_scope[:2]
        first_name = self._player_name(first)
        second_name = self._player_name(second)
        target_player_id, target_roster_id, counterparty_name = self._find_upgrade_target(
            league_id, roster_id, all_inputs
        )

        reasoning = (
            f"Package {first_name} + {second_name} -> target upgrade on the trade market."
        )
        target_player_name: str | None = None
        if target_player_id is not None and target_roster_id is not None:
            target_player_name = self._player_name(target_player_id)
            request = TradeRequest(
                league_id=league_id,
                user_roster_id=roster_id,
                counterparty_roster_id=target_roster_id,
                user_sends=[
                    TradeAsset(asset_type="player", player_id=first),
                    TradeAsset(asset_type="player", player_id=second),
                ],
                user_receives=[TradeAsset(asset_type="player", player_id=target_player_id)],
                include_package=True,
            )
            try:
                evaluation = self._trade_engine.evaluate(request)
                package = self._package_builder.build(request, evaluation)
            except Exception:
                package = None

            reasoning = (
                f"Package {first_name} + {second_name} -> target {target_player_name} "
                f"from {counterparty_name}."
            )
            if package is None:
                reasoning += " Package builder context was unavailable, but the trade shape still fits."

        return [
            self._suggestion(
                action_type="consolidate",
                league_id=league_id,
                inputs=inputs,
                primary_player_ids=[first, second],
                primary_player_names=[first_name, second_name],
                target_player_id=target_player_id,
                target_player_name=target_player_name,
                counterparty_roster_id=target_roster_id,
                counterparty_name=counterparty_name,
                reasoning=reasoning,
                direction_fit_score=0.65,
                timing_rationale=(
                    "Consolidate when you can turn two replaceable bench pieces into one lineup "
                    "upgrade before the market closes."
                ),
            )
        ]

    def _apply_coverage_guarantee(
        self,
        league_id: str,
        roster_id: int,
        inputs: ScorecardInputs,
        all_inputs: dict[int, ScorecardInputs],
        suggestions: list[HygieneSuggestion],
    ) -> list[HygieneSuggestion]:
        bench = self._bench_players(inputs)
        if len(bench) < 5:
            return suggestions

        metrics = self._player_metrics(league_id, roster_id, bench)
        action_types = {suggestion.action_type for suggestion in suggestions}

        if not action_types.intersection({"cut", "reroll_into_pick"}):
            lowest = min(
                bench,
                key=lambda player_id: float(
                    metrics.get(player_id, {}).get("lens_direction", 0.0)
                ),
                default=None,
            )
            if lowest is not None:
                lens = float(metrics.get(lowest, {}).get("lens_direction", 0.0))
                player_name = self._player_name(lowest)
                if lens > 0.05:
                    suggestions.append(
                        self._suggestion(
                            action_type="reroll_into_pick",
                            league_id=league_id,
                            inputs=inputs,
                            primary_player_ids=[lowest],
                            primary_player_names=[player_name],
                            reasoning=(
                                f"Reroll {player_name} into a late pick rather than holding a "
                                "soft dead spot."
                            ),
                            direction_fit_score=0.46,
                            timing_rationale=(
                                "Move now if anyone will attach a late pick before the roster spot "
                                "turns into pure dead weight."
                            ),
                        )
                    )
                elif self._transaction_count(lowest, league_id) > 0:
                    suggestions.append(
                        self._suggestion(
                            action_type="cut",
                            league_id=league_id,
                            inputs=inputs,
                            primary_player_ids=[lowest],
                            primary_player_names=[player_name],
                            reasoning=(
                                f"Cutting {player_name} frees a dead bench spot that is no longer "
                                "earning any usable upside."
                            ),
                            direction_fit_score=0.55,
                            timing_rationale=(
                                "Cut now to reclaim the slot before the next churn opportunity."
                            ),
                        )
                    )

        if "shop" not in action_types:
            shop_fallback = self._shop_suggestions(league_id, roster_id, inputs)
            if shop_fallback:
                suggestions.append(shop_fallback[0])
            else:
                roster_metrics = self._player_metrics(
                    league_id, roster_id, self._roster_players(inputs)
                )
                relaxed_shop_player = next(
                    (
                        player_id
                        for player_id in self._roster_players(inputs)
                        if (
                            inputs.adp_ranks.get(player_id) is not None
                            and inputs.adp_ranks[player_id] <= 80
                        )
                        or (
                            float(
                                roster_metrics.get(player_id, {}).get("lens_direction", 0.0)
                            )
                            >= 0.55
                            and int(inputs.player_ages.get(player_id, 24))
                            >= POSITIONAL_CLIFF_AGE.get(
                                inputs.player_positions.get(player_id, "UNKNOWN").upper(),
                                30,
                            )
                            - 2
                        )
                    ),
                    None,
                )
                if relaxed_shop_player is not None:
                    player_name = self._player_name(relaxed_shop_player)
                    lens = float(
                        roster_metrics.get(relaxed_shop_player, {}).get("lens_direction", 0.0)
                    )
                    suggestions.append(
                        self._suggestion(
                            action_type="shop",
                            league_id=league_id,
                            inputs=inputs,
                            primary_player_ids=[relaxed_shop_player],
                            primary_player_names=[player_name],
                            reasoning=(
                                f"Shop {player_name} as the most liquid veteran-style asset "
                                "available on this roster, even if the market is only moderate."
                            ),
                            direction_fit_score=max(0.45, lens),
                            timing_rationale=(
                                "Shop now while there is still enough market recognition to turn "
                                "this asset into cleaner value."
                            ),
                        )
                    )

        if not action_types.intersection({"package", "throw_in_now", "consolidate"}):
            package_fallback = self._package_suggestions(
                league_id, roster_id, inputs, all_inputs, "coverage"
            )
            if package_fallback:
                suggestions.append(package_fallback[0])
            elif len(bench) >= 2:
                first, second = bench[:2]
                first_name = self._player_name(first)
                second_name = self._player_name(second)
                suggestions.append(
                    self._suggestion(
                        action_type="package",
                        league_id=league_id,
                        inputs=inputs,
                        primary_player_ids=[first, second],
                        primary_player_names=[first_name, second_name],
                        reasoning=(
                            f"Package {first_name} + {second_name} rather than leaving both on "
                            "the bench as marginal assets."
                        ),
                        direction_fit_score=0.5,
                        timing_rationale=(
                            "Use the bench clutter in the next trade conversation instead of "
                            "letting both assets stagnate."
                        ),
                        packaging_rationale=(
                            f"{first_name} and {second_name} work better together as a sweetener "
                            "bundle than as isolated trade chips."
                        ),
                    )
                )

        return suggestions

    def _years_pro(
        self, player_id: str, season: int, inputs: ScorecardInputs
    ) -> int:
        row = self._conn.execute(
            "SELECT metadata_blob FROM players WHERE player_id = ?",
            [player_id],
        ).fetchone()
        meta = _loads(row[0] if row else None)
        draft_year = meta.get("years_exp") or meta.get("draft_year")
        if draft_year is not None:
            try:
                return max(0, int(season) - int(draft_year))
            except (TypeError, ValueError):
                pass
        age = int(inputs.player_ages.get(player_id, 22))
        return max(0, age - 22)
