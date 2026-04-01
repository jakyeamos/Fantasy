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
        owner_map = {
            int(row[0]): str(row[2] or row[1] or f"Roster {int(row[0])}")
            for row in self._conn.execute(
                """
                SELECT roster_id, owner_id, owner_display_name
                FROM rosters
                WHERE league_id = ?
                """,
                [league_id],
            ).fetchall()
        }
        league_row = self._conn.execute(
            """
            SELECT season, settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if league_row is None:
            return []

        current_season = int(league_row[0])
        league_settings = _loads(league_row[1], {})
        draft_rounds = max(int(league_settings.get("draft_rounds", 3) or 3), 1)
        future_seasons = [current_season + offset for offset in range(3)]

        traded_rows = [
            (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
            for row in self._conn.execute(
                """
                SELECT roster_id, owner_id, season, round
                FROM traded_picks
                WHERE league_id = ?
                  AND CAST(season AS INTEGER) >= ?
                """,
                [league_id, current_season],
            ).fetchall()
        ]
        traded_by_original = {
            (pick_year, round_no, original_owner_id): current_owner_id
            for original_owner_id, current_owner_id, pick_year, round_no in traded_rows
        }

        slot_by_pick = {
            (int(row[0]), int(row[1]), int(row[2])): float(row[3])
            for row in self._conn.execute(
                """
                SELECT pick_owner_roster_id, pick_year, pick_round, expected_draft_slot
                FROM pick_values
                WHERE league_id = ?
                """,
                [league_id],
            ).fetchall()
        }

        confirmed_by_roster_season: dict[tuple[int, int], int] = {}
        for row in self._conn.execute(
            """
            SELECT roster_id, season, confirmed_slot
            FROM draft_slots
            WHERE league_id = ?
            ORDER BY
                CASE status
                    WHEN 'complete'  THEN 0
                    WHEN 'drafting'  THEN 1
                    WHEN 'paused'    THEN 2
                    ELSE 3
                END,
                roster_id
            """,
            [league_id],
        ).fetchall():
            key = (int(row[0]), int(row[1]))
            if key not in confirmed_by_roster_season:
                confirmed_by_roster_season[key] = int(row[2])

        inventory: list[dict[str, Any]] = []
        for original_owner_id in sorted(owner_map):
            for pick_year in future_seasons:
                for round_no in range(1, draft_rounds + 1):
                    current_owner_id = traded_by_original.get(
                        (pick_year, round_no, original_owner_id), original_owner_id
                    )
                    if roster_id is not None and current_owner_id != roster_id:
                        continue
                    confirmed = confirmed_by_roster_season.get((original_owner_id, pick_year))
                    if confirmed is not None:
                        projected_slot = f"{round_no}.{confirmed:02d}"
                    else:
                        raw_slot = slot_by_pick.get((original_owner_id, pick_year, round_no))
                        projected_slot = (
                            f"~{round_no}.{int(round(raw_slot)):02d}"
                            if raw_slot is not None
                            else f"{round_no}.mid"
                        )
                    inventory.append(
                        {
                            "original_owner_id": original_owner_id,
                            "current_owner_id": current_owner_id,
                            "original_owner_name": owner_map.get(
                                original_owner_id, f"Roster {original_owner_id}"
                            ),
                            "pick_year": pick_year,
                            "round": round_no,
                            "projected_slot": projected_slot,
                            "current_owner_name": owner_map.get(
                                current_owner_id, f"Roster {current_owner_id}"
                            ),
                        }
                    )

        inventory.sort(
            key=lambda item: (
                item["pick_year"],
                item["round"],
                item["current_owner_id"],
                item["original_owner_id"],
            )
        )
        return inventory

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
