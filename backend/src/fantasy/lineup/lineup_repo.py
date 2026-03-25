from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.lineup.models import (
    HygieneResult,
    HygieneSuggestion,
    LeagueTaxiConfig,
    LineupResult,
    LineupSlotScore,
)


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class LineupRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0]) if row else 1

    def get_taxi_config(self, league_id: str) -> LeagueTaxiConfig | None:
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
                id, league_id, taxi_slots, taxi_years_eligible, years_pro_cutoff
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (league_id) DO UPDATE SET
                taxi_slots = EXCLUDED.taxi_slots,
                taxi_years_eligible = EXCLUDED.taxi_years_eligible,
                years_pro_cutoff = EXCLUDED.years_pro_cutoff,
                updated_at = now()
            """,
            [
                row_id,
                league_id,
                config.taxi_slots,
                config.taxi_years_eligible,
                config.years_pro_cutoff,
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
                slot_scores_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                total_lineup_score = EXCLUDED.total_lineup_score,
                title_window_label = EXCLUDED.title_window_label,
                title_window_composite = EXCLUDED.title_window_composite,
                ceiling_score = EXCLUDED.ceiling_score,
                stability_score = EXCLUDED.stability_score,
                depth_score = EXCLUDED.depth_score,
                slot_scores_json = EXCLUDED.slot_scores_json,
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
                slot_json,
            ],
        )

    def get_lineup_result(self, league_id: str, roster_id: int) -> LineupResult | None:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, CAST(computed_at AS VARCHAR),
                   total_lineup_score, title_window_label, title_window_composite,
                   ceiling_score, stability_score, depth_score, slot_scores_json
            FROM lineup_scores
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        slots_raw = _loads(row[9], [])
        slot_scores = [LineupSlotScore(**s) for s in slots_raw]
        return LineupResult(
            league_id=str(row[0]),
            roster_id=int(row[1]),
            computed_at=row[2],
            slot_scores=slot_scores,
            total_lineup_score=float(row[3]),
            title_window_label=str(row[4]),
            title_window_composite=float(row[5]),
            ceiling_score=float(row[6]),
            stability_score=float(row[7]),
            depth_score=float(row[8]),
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
                id, league_id, roster_id, suggestions_json
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                suggestions_json = EXCLUDED.suggestions_json,
                computed_at = now()
            """,
            [row_id, result.league_id, result.roster_id, sug_json],
        )

    def get_hygiene_result(self, league_id: str, roster_id: int) -> HygieneResult | None:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, CAST(computed_at AS VARCHAR), suggestions_json
            FROM hygiene_suggestions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        raw = _loads(row[3], [])
        suggestions = [HygieneSuggestion(**s) for s in raw]
        return HygieneResult(
            league_id=str(row[0]),
            roster_id=int(row[1]),
            computed_at=row[2],
            suggestions=suggestions,
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
