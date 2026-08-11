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


def _valid_player_ids(values: Sequence[Any]) -> list[str]:
    return [str(value) for value in values if value not in (None, "", 0, "0")]


class TradeRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_rosters(self, league_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT roster_id, owner_id, owner_display_name
            FROM rosters
            WHERE league_id = ?
            ORDER BY roster_id
            """,
            [league_id],
        ).fetchall()
        return [
            {
                "roster_id": int(row[0]),
                "roster_name": str(row[2] or row[1] or f"Roster {int(row[0])}"),
            }
            for row in rows
        ]

    def get_player_values(
        self, player_ids: Sequence[str], league_id: str, roster_id: int
    ) -> list[dict[str, Any]]:
        if not player_ids:
            return []
        placeholders = ",".join("?" for _ in player_ids)
        rows = self._conn.execute(
            f"""
            SELECT pv.roster_id, pv.player_id, p.full_name, p.position,
                   pv.comp_current_production, pv.comp_insulation, pv.comp_market_liquidity,
                   pv.comp_age_curve, pv.comp_ceiling, pv.comp_floor,
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
                "comp_current_production": float(row[4]) if row[4] is not None else None,
                "comp_insulation": float(row[5]) if row[5] is not None else None,
                "comp_market_liquidity": float(row[6]) if row[6] is not None else None,
                "comp_age_curve": float(row[7]) if row[7] is not None else None,
                "comp_ceiling": float(row[8]) if row[8] is not None else None,
                "comp_floor": float(row[9]) if row[9] is not None else None,
                "comp_positional_scarcity": float(row[10]) if row[10] is not None else None,
                "comp_short_term": float(row[11]) if row[11] is not None else None,
                "lens_market": float(row[12]) if row[12] is not None else None,
                "lens_insulation": float(row[13]) if row[13] is not None else None,
                "lens_team_fit": float(row[14]) if row[14] is not None else None,
                "lens_direction": float(row[15]) if row[15] is not None else None,
                "lens_production": float(row[16]) if row[16] is not None else None,
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

    def get_team_scorecard_context(
        self, league_id: str, roster_id: int
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            WITH latest AS (
                SELECT roster_id, win_now, future_value, depth, pick_capital,
                       flexibility, composite,
                       ROW_NUMBER() OVER (
                           PARTITION BY roster_id ORDER BY computed_at DESC NULLS LAST, id DESC
                       ) AS recency_rank
                FROM team_scorecards
                WHERE league_id = ?
            ), ranked AS (
                SELECT roster_id, win_now, future_value, depth, pick_capital,
                       flexibility, composite,
                       RANK() OVER (ORDER BY win_now DESC) AS win_now_rank,
                       RANK() OVER (ORDER BY future_value DESC) AS future_value_rank,
                       COUNT(*) OVER () AS roster_count
                FROM latest
                WHERE recency_rank = 1
            )
            SELECT win_now, future_value, depth, pick_capital, flexibility,
                   composite, win_now_rank, future_value_rank, roster_count
            FROM ranked
            WHERE roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        dominant_value_forward = (
            int(row[6]) == 1
            and int(row[7]) == 1
            and float(row[0]) >= 0.75
            and float(row[1]) >= 0.75
        )
        return {
            "win_now": float(row[0]),
            "future_value": float(row[1]),
            "depth": float(row[2]),
            "pick_capital": float(row[3]),
            "flexibility": float(row[4]),
            "composite": float(row[5]),
            "win_now_rank": int(row[6]),
            "future_value_rank": int(row[7]),
            "roster_count": int(row[8]),
            "posture": (
                "dominant_value_forward"
                if dominant_value_forward
                else "contender"
                if float(row[0]) >= 0.7
                else "future_focused"
                if float(row[1]) >= 0.7
                else "balanced"
            ),
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
        roster_rows = self._conn.execute(
            """
            SELECT roster_id, owner_id, owner_display_name, players
            FROM rosters
            WHERE league_id = ?
              AND (? IS NULL OR roster_id = ?)
            ORDER BY roster_id
            """,
            [league_id, roster_id, roster_id],
        ).fetchall()

        q_lower = q.strip().lower()
        results: list[dict[str, Any]] = []
        for row in roster_rows:
            current_roster_id = int(row[0])
            roster_name = str(row[2] or row[1] or f"Roster {current_roster_id}")
            player_ids = _valid_player_ids(_loads(row[3], []))
            if not player_ids:
                continue

            player_rows = {
                str(player[0]): {
                    "full_name": str(player[1] or player[0]),
                    "position": str(player[2] or "UNKNOWN"),
                    "team": str(player[3]) if player[3] is not None else None,
                }
                for player in self._conn.execute(
                    """
                    SELECT player_id, full_name, position, team
                    FROM players
                    WHERE player_id IN (
                        SELECT UNNEST(?)
                    )
                    """,
                    [player_ids],
                ).fetchall()
            }

            for player_id in player_ids:
                player = player_rows.get(
                    str(player_id),
                    {
                        "full_name": str(player_id),
                        "position": "UNKNOWN",
                        "team": None,
                    },
                )
                full_name = player["full_name"]
                position = player["position"]
                team = player["team"]
                if q_lower and (
                    q_lower not in full_name.lower()
                    and q_lower not in position.lower()
                    and q_lower not in str(player_id).lower()
                    and (team is None or q_lower not in team.lower())
                ):
                    continue
                results.append(
                    {
                        "player_id": str(player_id),
                        "full_name": full_name,
                        "position": position,
                        "team": team,
                        "roster_id": current_roster_id,
                        "roster_name": roster_name,
                    }
                )
        results.sort(key=lambda item: (item["full_name"], item["roster_id"], item["player_id"]))
        if roster_id is not None:
            return results
        return results[:PLAYER_SEARCH_LIMIT]

    def get_picks_for_league(
        self, league_id: str, roster_id: int | None = None
    ) -> list[dict[str, Any]]:
        from fantasy.picks.pick_repo import PickRepo

        return [
            row
            for row in PickRepo(self._conn).get_pick_inventory_rows(
                league_id,
                extend_to_traded_horizon=True,
            )
            if roster_id is None or int(row["current_owner_id"]) == roster_id
        ]

    def get_pick_value(
        self,
        pick: dict[str, Any] | Any,
        league_id: str,
        target_roster_id: int | None = None,
    ):
        from fantasy.picks.pick_engine import PickEngine

        return PickEngine(self._conn).compute(
            pick,
            league_id,
            target_manager_id=target_roster_id,
        )

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
        player_ids = _valid_player_ids(_loads(row[0], []))
        if not player_ids:
            return []
        player_rows = {
            str(item[0]): {
                "full_name": str(item[1] or item[0]),
                "position": str(item[2] or "UNKNOWN"),
            }
            for item in self._conn.execute(
                """
                SELECT player_id, full_name, position
                FROM players
                WHERE player_id IN (
                    SELECT UNNEST(?)
                )
                """,
                [player_ids],
            ).fetchall()
        }
        return [
            {
                "player_id": str(player_id),
                "full_name": player_rows.get(str(player_id), {}).get("full_name", str(player_id)),
                "position": player_rows.get(str(player_id), {}).get("position", "UNKNOWN"),
            }
            for player_id in player_ids
        ]
