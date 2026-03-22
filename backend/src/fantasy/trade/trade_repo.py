from __future__ import annotations

import json
from typing import Any, Sequence

import duckdb

from fantasy.trade.constants import PLAYER_SEARCH_LIMIT


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class TradeRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_player_values(
        self, player_ids: Sequence[str], league_id: str, roster_id: int
    ) -> list[dict[str, Any]]:
        if not player_ids:
            return []
        placeholders = ",".join("?" for _ in player_ids)
        rows = self._conn.execute(
            f"""
            SELECT pv.roster_id, pv.player_id, p.full_name, p.position,
                   pv.comp_insulation, pv.comp_market_liquidity, pv.comp_age_curve,
                   pv.comp_positional_scarcity, pv.comp_short_term, pv.lens_market,
                   pv.lens_insulation, pv.lens_team_fit, pv.lens_direction,
                   pv.lens_production
            FROM player_values pv
            LEFT JOIN players p ON p.player_id = pv.player_id
            WHERE pv.league_id = ?
              AND pv.player_id IN ({placeholders})
            ORDER BY CASE WHEN pv.roster_id = ? THEN 0 ELSE 1 END, pv.roster_id
            """,
            [league_id, *player_ids, roster_id],
        ).fetchall()
        chosen: dict[str, dict[str, Any]] = {}
        for row in rows:
            player_id = str(row[1])
            if player_id in chosen:
                continue
            chosen[player_id] = {
                "roster_id": int(row[0]),
                "player_id": player_id,
                "full_name": str(row[2] or player_id),
                "position": str(row[3] or "UNKNOWN"),
                "comp_insulation": float(row[4]) if row[4] is not None else None,
                "comp_market_liquidity": float(row[5]) if row[5] is not None else None,
                "comp_age_curve": float(row[6]) if row[6] is not None else None,
                "comp_positional_scarcity": float(row[7]) if row[7] is not None else None,
                "comp_short_term": float(row[8]) if row[8] is not None else None,
                "lens_market": float(row[9]) if row[9] is not None else None,
                "lens_insulation": float(row[10]) if row[10] is not None else None,
                "lens_team_fit": float(row[11]) if row[11] is not None else None,
                "lens_direction": float(row[12]) if row[12] is not None else None,
                "lens_production": float(row[13]) if row[13] is not None else None,
            }
        return [chosen[player_id] for player_id in player_ids if player_id in chosen]

    def get_team_direction(self, league_id: str, roster_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT primary_label, confidence, approved_moves, discouraged_moves
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "primary_label": str(row[0]),
            "confidence": float(row[1]),
            "approved_moves": _loads(row[2], []),
            "discouraged_moves": _loads(row[3], []),
        }

    def get_manager_profile(self, league_id: str, roster_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT exploitability_score, exploitation_primary, exploitation_secondary,
                   evidence_count, low_confidence
            FROM manager_profiles
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "exploitability_score": float(row[0]),
            "exploitation_primary": str(row[1]) if row[1] is not None else None,
            "exploitation_secondary": str(row[2]) if row[2] is not None else None,
            "evidence_count": int(row[3]),
            "low_confidence": bool(row[4]),
        }

    def get_pitch_angles(self, league_id: str, roster_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT deal_archetype, send_description, avoid_description, reasoning
            FROM manager_pitch_angles
            WHERE league_id = ? AND roster_id = ?
            ORDER BY rank
            """,
            [league_id, roster_id],
        ).fetchall()
        return [
            {
                "deal_archetype": str(row[0]),
                "send_description": str(row[1]),
                "avoid_description": str(row[2]),
                "reasoning": str(row[3]),
            }
            for row in rows
        ]

    def search_players(
        self, league_id: str, q: str, roster_id: int | None = None
    ) -> list[dict[str, Any]]:
        roster_params: list[Any] = [league_id]
        roster_sql = """
            SELECT roster_id, owner_id, players
            FROM rosters
            WHERE league_id = ?
        """
        if roster_id is not None:
            roster_sql += " AND roster_id = ?"
            roster_params.append(roster_id)
        roster_rows = self._conn.execute(roster_sql, roster_params).fetchall()

        q_lower = q.lower()
        results: list[dict[str, Any]] = []
        for row in roster_rows:
            current_roster_id = int(row[0])
            roster_name = str(row[1] or f"Roster {current_roster_id}")
            player_ids = _loads(row[2], [])
            if not player_ids:
                continue
            placeholders = ",".join("?" for _ in player_ids)
            players = self._conn.execute(
                f"""
                SELECT player_id, full_name, position, team
                FROM players
                WHERE player_id IN ({placeholders})
                """,
                player_ids,
            ).fetchall()
            for player in players:
                full_name = str(player[1] or player[0])
                position = str(player[2] or "UNKNOWN")
                if q_lower not in full_name.lower() and q_lower not in position.lower():
                    continue
                results.append(
                    {
                        "player_id": str(player[0]),
                        "full_name": full_name,
                        "position": position,
                        "team": str(player[3]) if player[3] is not None else None,
                        "roster_id": current_roster_id,
                        "roster_name": roster_name,
                    }
                )
        results.sort(key=lambda item: (item["full_name"], item["roster_id"]))
        return results[:PLAYER_SEARCH_LIMIT]

    def get_picks_for_league(
        self, league_id: str, roster_id: int | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT roster_id, owner_id, season, round
            FROM traded_picks
            WHERE league_id = ?
        """
        params: list[Any] = [league_id]
        if roster_id is not None:
            sql += " AND owner_id = ?"
            params.append(str(roster_id))
        sql += " ORDER BY season, round"
        owner_map = {
            int(row[0]): str(row[1] or f"Roster {int(row[0])}")
            for row in self._conn.execute(
                """
                SELECT roster_id, owner_id
                FROM rosters
                WHERE league_id = ?
                """,
                [league_id],
            ).fetchall()
        }
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "original_owner_id": int(row[0]),
                "current_owner_id": int(row[1]),
                "pick_year": int(row[2]),
                "round": int(row[3]),
                "projected_slot": f"{int(row[3])}.mid",
                "current_owner_name": owner_map.get(int(row[1]), f"Roster {int(row[1])}"),
            }
            for row in rows
        ]

    def get_roster_players(self, league_id: str, roster_id: int) -> list[dict[str, Any]]:
        row = self._conn.execute(
            """
            SELECT players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return []
        player_ids = _loads(row[0], [])
        if not player_ids:
            return []
        placeholders = ",".join("?" for _ in player_ids)
        rows = self._conn.execute(
            f"""
            SELECT player_id, full_name, position
            FROM players
            WHERE player_id IN ({placeholders})
            """,
            player_ids,
        ).fetchall()
        return [
            {
                "player_id": str(item[0]),
                "full_name": str(item[1] or item[0]),
                "position": str(item[2] or "UNKNOWN"),
            }
            for item in rows
        ]
