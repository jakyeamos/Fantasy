from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.rookie_pick.models import DraftPickSelection, RookiePickProfile


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class RookiePickRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0])

    def get_profile(self, league_id: str, roster_id: int) -> RookiePickProfile | None:
        row = self._conn.execute(
            """
            SELECT league_id, roster_id, CAST(computed_at AS VARCHAR), pick_premium_score,
                   pick_trade_evidence, draft_selection_count, positional_tendency_json,
                   dominant_archetype, archetype_pattern_json, show_draft_picks_tab
            FROM manager_rookie_pick_profiles
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return RookiePickProfile(
            league_id=str(row[0]),
            roster_id=int(row[1]),
            computed_at=str(row[2]),
            pick_premium_score=float(row[3]) if row[3] is not None else None,
            pick_trade_evidence=int(row[4]),
            draft_selection_count=int(row[5]),
            positional_tendency=_loads(row[6], {}),
            dominant_archetype=str(row[7]) if row[7] is not None else None,
            archetype_pattern=_loads(row[8], {}),
            show_draft_picks_tab=bool(row[9]),
            draft_selection_history=self.get_draft_selections(league_id, roster_id),
        )

    def upsert_profile(self, profile: RookiePickProfile) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM manager_rookie_pick_profiles
            WHERE league_id = ? AND roster_id = ?
            """,
            [profile.league_id, profile.roster_id],
        ).fetchone()
        row_id = (
            int(existing[0]) if existing else self._next_id("manager_rookie_pick_profiles")
        )
        self._conn.execute(
            """
            INSERT INTO manager_rookie_pick_profiles (
                id, league_id, roster_id, computed_at, pick_premium_score,
                pick_trade_evidence, draft_selection_count, positional_tendency_json,
                dominant_archetype, archetype_pattern_json, show_draft_picks_tab
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                computed_at = EXCLUDED.computed_at,
                pick_premium_score = EXCLUDED.pick_premium_score,
                pick_trade_evidence = EXCLUDED.pick_trade_evidence,
                draft_selection_count = EXCLUDED.draft_selection_count,
                positional_tendency_json = EXCLUDED.positional_tendency_json,
                dominant_archetype = EXCLUDED.dominant_archetype,
                archetype_pattern_json = EXCLUDED.archetype_pattern_json,
                show_draft_picks_tab = EXCLUDED.show_draft_picks_tab
            """,
            [
                row_id,
                profile.league_id,
                profile.roster_id,
                profile.computed_at,
                profile.pick_premium_score,
                profile.pick_trade_evidence,
                profile.draft_selection_count,
                json.dumps(profile.positional_tendency, separators=(",", ":")),
                profile.dominant_archetype,
                json.dumps(profile.archetype_pattern, separators=(",", ":")),
                profile.show_draft_picks_tab,
            ],
        )

    def upsert_draft_selection(self, sel: DraftPickSelection | dict[str, Any]) -> None:
        payload = (
            sel.model_dump() if isinstance(sel, DraftPickSelection) else dict(sel)
        )
        existing = self._conn.execute(
            """
            SELECT id
            FROM draft_pick_selections
            WHERE league_id = ? AND draft_id = ? AND roster_id = ? AND player_id = ?
            """,
            [
                payload["league_id"],
                payload["draft_id"],
                payload["roster_id"],
                payload["player_id"],
            ],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("draft_pick_selections")
        self._conn.execute(
            """
            INSERT INTO draft_pick_selections (
                id, league_id, draft_id, roster_id, player_id, pick_slot,
                round_number, season, draft_type, position, archetype_label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, draft_id, roster_id, player_id) DO UPDATE SET
                pick_slot = EXCLUDED.pick_slot,
                round_number = EXCLUDED.round_number,
                season = EXCLUDED.season,
                draft_type = EXCLUDED.draft_type,
                position = EXCLUDED.position,
                archetype_label = EXCLUDED.archetype_label
            """,
            [
                row_id,
                payload["league_id"],
                payload["draft_id"],
                payload["roster_id"],
                payload["player_id"],
                payload["pick_slot"],
                payload["round_number"],
                payload["season"],
                payload["draft_type"],
                payload.get("position"),
                payload.get("archetype_label"),
            ],
        )

    def get_draft_selections(self, league_id: str, roster_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT player_id, pick_slot, round_number, season, draft_type, position, archetype_label
            FROM draft_pick_selections
            WHERE league_id = ? AND roster_id = ?
            ORDER BY season DESC, pick_slot ASC
            """,
            [league_id, roster_id],
        ).fetchall()
        columns = [
            "player_id",
            "pick_slot",
            "round_number",
            "season",
            "draft_type",
            "position",
            "archetype_label",
        ]
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def get_all_league_selections(self, league_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT roster_id, player_id, pick_slot, round_number, season, draft_type, position, archetype_label
            FROM draft_pick_selections
            WHERE league_id = ?
            ORDER BY season DESC, pick_slot ASC
            """,
            [league_id],
        ).fetchall()
        columns = [
            "roster_id",
            "player_id",
            "pick_slot",
            "round_number",
            "season",
            "draft_type",
            "position",
            "archetype_label",
        ]
        return [dict(zip(columns, row, strict=False)) for row in rows]
