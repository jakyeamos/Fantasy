from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.lineup.constants import UPGRADE_LEVERAGE_BASE_EQUITY
from fantasy.lineup.models import (
    HygieneResult,
    HygieneSuggestion,
    LeagueTaxiConfig,
    LineupResult,
    LineupSlotScore,
)
from fantasy.recommendation.models import RecommendationCard


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


_REQUIRED_LINEUP_SLOT_KEYS = {
    "contender_benchmark",
    "playoff_target",
    "title_target",
    "elite_target",
    "upgrade_leverage_score",
    "gap_to_playoff_target",
    "gap_to_title_target",
    "gap_to_elite_target",
    "weak_by_median",
    "below_playoff_target",
    "below_title_target",
    "below_elite_target",
    "weak_relative_to_contender",
    "benchmark_used",
    "benchmark_source",
    "benchmark_sample_size",
    "elite_insulation_guard",
    "format_urgency_weight",
    "player_context_flags",
}

_REQUIRED_HYGIENE_SUGGESTION_KEYS = {
    "timing_rationale",
    "player_context_flags",
}


def _lineup_cache_complete(slots_raw: Any) -> bool:
    if not isinstance(slots_raw, list):
        return False
    return all(
        isinstance(slot, dict) and _REQUIRED_LINEUP_SLOT_KEYS.issubset(slot)
        for slot in slots_raw
    )


def _hygiene_cache_complete(suggestions_raw: Any) -> bool:
    if not isinstance(suggestions_raw, list):
        return False
    return all(
        isinstance(suggestion, dict)
        and _REQUIRED_HYGIENE_SUGGESTION_KEYS.issubset(suggestion)
        and bool(str(suggestion.get("timing_rationale", "")).strip())
        for suggestion in suggestions_raw
    )


class LineupRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0]) if row else 1

    def get_taxi_config(self, league_id: str) -> LeagueTaxiConfig | None:
        try:
            row = self._conn.execute(
                """
                SELECT taxi_slots,
                       taxi_years_eligible,
                       years_pro_cutoff,
                       COALESCE(manual_exceptions_json, '[]') AS manual_exceptions_json
                FROM league_taxi_configs
                WHERE league_id = ?
                LIMIT 1
                """,
                [league_id],
            ).fetchone()
        except duckdb.Error:
            row = self._conn.execute(
                """
                SELECT taxi_slots, taxi_years_eligible, years_pro_cutoff
                FROM league_taxi_configs
                WHERE league_id = ?
                LIMIT 1
                """,
                [league_id],
            ).fetchone()
        if row is None:
            return None
        return LeagueTaxiConfig(
            taxi_slots=int(row[0]),
            taxi_years_eligible=int(row[1]),
            years_pro_cutoff=int(row[2]),
            manual_exceptions=_loads(row[3] if len(row) > 3 else None, []),
        )

    def save_taxi_config(self, league_id: str, config: LeagueTaxiConfig) -> LeagueTaxiConfig:
        existing = self._conn.execute(
            "SELECT id FROM league_taxi_configs WHERE league_id = ?",
            [league_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("league_taxi_configs")
        self._conn.execute(
            """
            INSERT INTO league_taxi_configs (
                id, league_id, taxi_slots, taxi_years_eligible, years_pro_cutoff,
                manual_exceptions_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id) DO UPDATE SET
                taxi_slots = EXCLUDED.taxi_slots,
                taxi_years_eligible = EXCLUDED.taxi_years_eligible,
                years_pro_cutoff = EXCLUDED.years_pro_cutoff,
                manual_exceptions_json = EXCLUDED.manual_exceptions_json,
                updated_at = now()
            """,
            [
                row_id,
                league_id,
                config.taxi_slots,
                config.taxi_years_eligible,
                config.years_pro_cutoff,
                json.dumps(config.manual_exceptions, separators=(",", ":")),
            ],
        )
        return config

    def save_lineup_result(self, result: LineupResult) -> None:
        slot_json = json.dumps(
            [s.model_dump() for s in result.slot_scores],
            separators=(",", ":"),
        )
        existing = self._conn.execute(
            """
            SELECT id FROM lineup_scores
            WHERE league_id = ? AND roster_id = ?
            """,
            [result.league_id, result.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("lineup_scores")
        self._conn.execute(
            """
            INSERT INTO lineup_scores (
                id, league_id, roster_id, total_lineup_score, title_window_label,
                title_window_composite, ceiling_score, stability_score, depth_score,
                overall_playoff_target, overall_title_target, overall_elite_target,
                overall_gap_to_playoff_target, overall_gap_to_title_target,
                overall_gap_to_elite_target, overall_benchmark_source,
                overall_benchmark_sample_size, slot_scores_json, recommendation_cards_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                total_lineup_score = EXCLUDED.total_lineup_score,
                title_window_label = EXCLUDED.title_window_label,
                title_window_composite = EXCLUDED.title_window_composite,
                ceiling_score = EXCLUDED.ceiling_score,
                stability_score = EXCLUDED.stability_score,
                depth_score = EXCLUDED.depth_score,
                overall_playoff_target = EXCLUDED.overall_playoff_target,
                overall_title_target = EXCLUDED.overall_title_target,
                overall_elite_target = EXCLUDED.overall_elite_target,
                overall_gap_to_playoff_target = EXCLUDED.overall_gap_to_playoff_target,
                overall_gap_to_title_target = EXCLUDED.overall_gap_to_title_target,
                overall_gap_to_elite_target = EXCLUDED.overall_gap_to_elite_target,
                overall_benchmark_source = EXCLUDED.overall_benchmark_source,
                overall_benchmark_sample_size = EXCLUDED.overall_benchmark_sample_size,
                slot_scores_json = EXCLUDED.slot_scores_json,
                recommendation_cards_json = EXCLUDED.recommendation_cards_json,
                computed_at = now()
            """,
            [
                row_id,
                result.league_id,
                result.roster_id,
                result.total_lineup_score,
                result.title_window_label,
                result.title_window_composite,
                result.ceiling_score,
                result.stability_score,
                result.depth_score,
                result.overall_playoff_target,
                result.overall_title_target,
                result.overall_elite_target,
                result.overall_gap_to_playoff_target,
                result.overall_gap_to_title_target,
                result.overall_gap_to_elite_target,
                result.overall_benchmark_source,
                result.overall_benchmark_sample_size,
                slot_json,
                json.dumps(
                    [card.model_dump() for card in result.recommendation_cards or []],
                    separators=(",", ":"),
                ),
            ],
        )

    def get_lineup_result(self, league_id: str, roster_id: int) -> LineupResult | None:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, CAST(computed_at AS VARCHAR),
                   total_lineup_score, title_window_label, title_window_composite,
                   ceiling_score, stability_score, depth_score, overall_playoff_target,
                   overall_title_target, overall_elite_target,
                   overall_gap_to_playoff_target, overall_gap_to_title_target,
                   overall_gap_to_elite_target, overall_benchmark_source,
                   overall_benchmark_sample_size, slot_scores_json,
                   recommendation_cards_json
            FROM lineup_scores
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        if any(row[index] is None for index in range(9, 17)):
            return None
        slots_raw = _loads(row[17], [])
        if not _lineup_cache_complete(slots_raw):
            return None
        slot_scores = [LineupSlotScore(**s) for s in slots_raw]
        cards_raw = _loads(row[18], [])
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
        return LineupResult(
            league_id=str(row[0]),
            roster_id=int(row[1]),
            computed_at=row[2],
            slot_scores=slot_scores,
            total_lineup_score=float(row[3]),
            overall_playoff_target=float(row[9]),
            overall_title_target=float(row[10]),
            overall_elite_target=float(row[11]),
            overall_gap_to_playoff_target=float(row[12]),
            overall_gap_to_title_target=float(row[13]),
            overall_gap_to_elite_target=float(row[14]),
            overall_benchmark_source=str(row[15]),
            overall_benchmark_sample_size=int(row[16]),
            title_window_label=str(row[4]),
            title_window_composite=float(row[5]),
            ceiling_score=float(row[6]),
            stability_score=float(row[7]),
            depth_score=float(row[8]),
            recommendation_cards=[RecommendationCard(**card) for card in cards_raw],
            contender_benchmark_used=any(slot.benchmark_used for slot in slot_scores),
            upgrade_leverage_point=(
                f"{best_slot.player_name} ({best_slot.position})"
                if best_slot
                else ""
            ),
            upgrade_title_equity_delta=float(
                min(1.0, weighted_leverage * UPGRADE_LEVERAGE_BASE_EQUITY)
            ),
        )

    def save_hygiene_result(self, result: HygieneResult) -> None:
        sug_json = json.dumps(
            [s.model_dump() for s in result.suggestions],
            separators=(",", ":"),
        )
        existing = self._conn.execute(
            """
            SELECT id FROM hygiene_suggestions
            WHERE league_id = ? AND roster_id = ?
            """,
            [result.league_id, result.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("hygiene_suggestions")
        self._conn.execute(
            """
            INSERT INTO hygiene_suggestions (
                id, league_id, roster_id, suggestions_json, recommendation_cards_json
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                suggestions_json = EXCLUDED.suggestions_json,
                recommendation_cards_json = EXCLUDED.recommendation_cards_json,
                computed_at = now()
            """,
            [
                row_id,
                result.league_id,
                result.roster_id,
                sug_json,
                json.dumps(
                    [card.model_dump() for card in result.recommendation_cards or []],
                    separators=(",", ":"),
                ),
            ],
        )

    def get_hygiene_result(self, league_id: str, roster_id: int) -> HygieneResult | None:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, CAST(computed_at AS VARCHAR), suggestions_json,
                   recommendation_cards_json
            FROM hygiene_suggestions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        raw = _loads(row[3], [])
        if not _hygiene_cache_complete(raw):
            return None
        suggestions = [HygieneSuggestion(**s) for s in raw]
        cards = [RecommendationCard(**card) for card in _loads(row[4], [])]
        return HygieneResult(
            league_id=str(row[0]),
            roster_id=int(row[1]),
            computed_at=row[2],
            suggestions=suggestions,
            recommendation_cards=cards,
        )

    def get_slot_occupancy(self, league_id: str, roster_id: int) -> dict:
        roster_row = self._conn.execute(
            """
            SELECT reserve, taxi
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if roster_row is None:
            return {
                "taxi_used": 0,
                "taxi_total": 0,
                "ir_used": 0,
                "ir_total": 0,
            }

        ir_list = _loads(roster_row[0], [])
        taxi_list = _loads(roster_row[1], [])
        taxi_config = self.get_taxi_config(league_id)
        taxi_total = int(taxi_config.taxi_slots) if taxi_config else 0

        league_row = self._conn.execute(
            """
            SELECT settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        settings = _loads(league_row[0] if league_row else None, {}) or {}
        ir_total = int(settings.get("ir_slots", settings.get("reserve_slots", 0)) or 0)

        return {
            "taxi_used": len(taxi_list),
            "taxi_total": taxi_total,
            "ir_used": len(ir_list),
            "ir_total": ir_total,
        }
