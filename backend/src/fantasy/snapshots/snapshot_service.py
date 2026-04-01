from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import duckdb


WEAKNESS_LABELS: dict[str, str] = {
    "win_now": "Your lineup needs more weekly production to compete now.",
    "future_value": "Your roster lacks enough insulated long-term value.",
    "depth": "You need more playable depth behind your starters.",
    "pick_capital": "You need more draft capital to unlock flexible moves.",
    "flexibility": "Position mix is skewed toward one position group.",
    "fragility": "Your weekly outcomes are too brittle to injuries or misses.",
    "age_risk": "Your core is carrying too much age-related downside.",
    "liquidity": "Your roster lacks enough liquid market assets to move.",
    "positional_insulation": "You need more insulation at scarce lineup spots.",
}

HIGHER_IS_WORSE_FIELDS = {"fragility", "age_risk"}

SCORECARD_FIELDS = [
    "win_now",
    "future_value",
    "depth",
    "pick_capital",
    "flexibility",
    "fragility",
    "age_risk",
    "liquidity",
    "positional_insulation",
]


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _position_group_phrase(position: str, count: int) -> tuple[str, str]:
    labels = {
        "QB": ("QB", "QBs"),
        "RB": ("RB", "RBs"),
        "WR": ("WR", "WRs"),
        "TE": ("TE", "TEs"),
        "K": ("K", "Ks"),
        "DEF": ("DEF", "DEFs"),
        "DL": ("DL", "DLs"),
        "LB": ("LB", "LBs"),
        "DB": ("DB", "DBs"),
        "UNKNOWN": ("Unknown-position player", "Unknown-position players"),
    }
    singular, plural = labels.get(position, (position, f"{position}s"))
    return (singular, "is") if count == 1 else (plural, "are")


class SnapshotService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def take_snapshot(
        self,
        league_ids: list[str],
        triggered_by: str,
        ingest_run_id: int | None = None,
    ) -> list[int]:
        all_rows = self.conn.execute(
            "SELECT league_id FROM leagues ORDER BY league_id"
        ).fetchall()
        connected_league_ids = [str(row[0]) for row in all_rows]
        if not connected_league_ids:
            return []

        snapshot_ids: list[int] = []
        for league_id in connected_league_ids:
            snapshot_type, base_snapshot_id = self._resolve_snapshot_type(league_id)
            current_state = self._build_league_state(league_id)
            previous_state = self._load_previous_state(league_id)

            payload: dict[str, Any] = {
                "league_id": league_id,
                "trigger_context": {
                    "requested_league_ids": league_ids,
                    "triggered_by": triggered_by,
                    "ingest_run_id": ingest_run_id,
                },
                "state": current_state,
            }
            if snapshot_type == "delta":
                payload["delta"] = self._compute_delta(previous_state, current_state)

            next_id = self._next_id()
            self.conn.execute(
                """
                INSERT INTO league_snapshots (
                    id, league_id, snapshot_type, triggered_by, ingest_run_id,
                    payload_json, base_snapshot_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    league_id,
                    snapshot_type,
                    triggered_by,
                    ingest_run_id,
                    json.dumps(payload, separators=(",", ":")),
                    base_snapshot_id,
                ],
            )
            snapshot_ids.append(next_id)
        return snapshot_ids

    def _next_id(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM league_snapshots"
        ).fetchone()
        return int(row[0])

    def _resolve_snapshot_type(self, league_id: str) -> tuple[str, int | None]:
        full_row = self.conn.execute(
            """
            SELECT id
            FROM league_snapshots
            WHERE league_id = ?
              AND snapshot_type = 'full'
              AND DATE_TRUNC('month', snapshot_at) = DATE_TRUNC('month', CURRENT_TIMESTAMP)
            ORDER BY snapshot_at DESC
            LIMIT 1
            """,
            [league_id],
        ).fetchone()

        if full_row is None:
            return "full", None

        latest_full = self.conn.execute(
            """
            SELECT id
            FROM league_snapshots
            WHERE league_id = ? AND snapshot_type = 'full'
            ORDER BY snapshot_at DESC
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        return "delta", int(latest_full[0]) if latest_full else None

    def _load_previous_state(self, league_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            SELECT payload_json
            FROM league_snapshots
            WHERE league_id = ?
            ORDER BY snapshot_at DESC, id DESC
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None or row[0] is None:
            return {}
        payload = _loads(row[0], {})
        if isinstance(payload, dict):
            return payload.get("state", {}) or {}
        return {}

    def _build_league_state(self, league_id: str) -> dict[str, Any]:
        league_row = self.conn.execute(
            "SELECT name, season FROM leagues WHERE league_id = ?",
            [league_id],
        ).fetchone()
        league_name = str(league_row[0]) if league_row else league_id
        season = str(league_row[1]) if league_row else ""

        standing_rows = self.conn.execute(
            """
            SELECT roster_id, wins, losses, ties, fpts, fpts_against
            FROM standings
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        standings = {
            int(row[0]): {
                "wins": int(row[1]),
                "losses": int(row[2]),
                "ties": int(row[3]),
                "fpts": float(row[4]),
                "fpts_against": float(row[5]),
            }
            for row in standing_rows
        }

        direction_rows = self.conn.execute(
            """
            SELECT roster_id, primary_label, confidence
            FROM team_directions
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        directions = {
            int(row[0]): {
                "label": str(row[1]),
                "confidence": float(row[2]),
            }
            for row in direction_rows
        }

        scorecard_rows = self.conn.execute(
            """
            SELECT roster_id, win_now, future_value, depth, pick_capital, flexibility,
                   fragility, age_risk, liquidity, positional_insulation
            FROM team_scorecards
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        scorecards = {
            int(row[0]): {
                field: float(value)
                for field, value in zip(SCORECARD_FIELDS, row[1:], strict=False)
            }
            for row in scorecard_rows
        }
        player_positions = {
            str(row[0]): str(row[1] or "UNKNOWN")
            for row in self.conn.execute(
                "SELECT player_id, position FROM players"
            ).fetchall()
        }

        player_value_rows = self.conn.execute(
            """
            SELECT pv.roster_id, pv.player_id, p.full_name, p.position,
                   pv.lens_market, pv.lens_direction, pv.lens_team_fit,
                   pv.comp_short_term, pv.comp_age_curve
            FROM player_values pv
            LEFT JOIN players p ON p.player_id = pv.player_id
            WHERE pv.league_id = ?
            ORDER BY pv.roster_id, pv.player_id
            """,
            [league_id],
        ).fetchall()
        player_values: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in player_value_rows:
            player_values[int(row[0])].append(
                {
                    "player_id": str(row[1]),
                    "player_name": str(row[2] or row[1]),
                    "position": str(row[3] or "UNKNOWN"),
                    "lens_market": float(row[4]) if row[4] is not None else None,
                    "lens_direction": float(row[5]) if row[5] is not None else None,
                    "lens_team_fit": float(row[6]) if row[6] is not None else None,
                    "comp_short_term": float(row[7]) if row[7] is not None else None,
                    "comp_age_curve": float(row[8]) if row[8] is not None else None,
                }
            )

        roster_rows = self.conn.execute(
            """
            SELECT roster_id, owner_id, starters, players, reserve, taxi
            FROM rosters
            WHERE league_id = ?
            ORDER BY roster_id
            """,
            [league_id],
        ).fetchall()
        rosters: list[dict[str, Any]] = []
        for row in roster_rows:
            roster_id = int(row[0])
            scorecard = scorecards.get(roster_id, {})
            starters = _loads(row[2], [])
            players = _loads(row[3], [])
            reserve = _loads(row[4], [])
            taxi = _loads(row[5], [])
            rosters.append(
                {
                    "roster_id": roster_id,
                    "owner_id": row[1],
                    "starters": starters,
                    "players": players,
                    "reserve": reserve,
                    "taxi": taxi,
                    "standing": standings.get(roster_id),
                    "direction": directions.get(roster_id),
                    "scorecard": scorecard,
                    "primary_weakness": self._derive_primary_weakness(
                        scorecard,
                        starters=starters,
                        players=players,
                        reserve=reserve,
                        taxi=taxi,
                        player_positions=player_positions,
                    ),
                    "player_values": player_values.get(roster_id, []),
                }
            )

        capital_scores: dict[int, float] = {}
        try:
            from fantasy.picks.pick_engine import PickEngine

            pick_engine = PickEngine(self.conn)
            for roster in rosters:
                current_roster_id = int(roster["roster_id"])
                capital_scores[current_roster_id] = pick_engine.compute_capital_score(
                    league_id=league_id,
                    roster_id=current_roster_id,
                )
        except Exception:
            capital_scores = {}

        for roster in rosters:
            roster["capital_score"] = capital_scores.get(int(roster["roster_id"]))

        traded_pick_rows = self.conn.execute(
            """
            SELECT season, round, roster_id, owner_id, previous_owner_id
            FROM traded_picks
            WHERE league_id = ?
            ORDER BY season, round, roster_id
            """,
            [league_id],
        ).fetchall()
        traded_picks = [
            {
                "season": str(row[0]),
                "round": int(row[1]),
                "roster_id": int(row[2]),
                "owner_id": row[3],
                "previous_owner_id": row[4],
            }
            for row in traded_pick_rows
        ]

        return {
            "league_name": league_name,
            "season": season,
            "rosters": rosters,
            "traded_picks": traded_picks,
        }

    def _build_flexibility_note(
        self,
        starters: list[Any],
        players: list[Any],
        reserve: list[Any],
        taxi: list[Any],
        player_positions: dict[str, str],
    ) -> str | None:
        starter_ids = [str(player_id) for player_id in starters]
        excluded = set(starter_ids) | {str(player_id) for player_id in reserve} | {
            str(player_id) for player_id in taxi
        }
        roster = starter_ids + [
            str(player_id) for player_id in players if str(player_id) not in excluded
        ]
        if not roster:
            return None

        counts: dict[str, int] = {}
        for player_id in roster:
            position = player_positions.get(player_id, "UNKNOWN")
            counts[position] = counts.get(position, 0) + 1

        dominant_position, dominant_count = max(
            counts.items(), key=lambda item: (item[1], item[0])
        )
        label, verb = _position_group_phrase(dominant_position, dominant_count)
        share = round((dominant_count / len(roster)) * 100)
        return f"{label} {verb} {dominant_count} of {len(roster)} starters/bench players ({share}%)."

    def _derive_primary_weakness(
        self,
        scorecard: dict[str, float],
        *,
        starters: list[Any] | None = None,
        players: list[Any] | None = None,
        reserve: list[Any] | None = None,
        taxi: list[Any] | None = None,
        player_positions: dict[str, str] | None = None,
    ) -> str:
        if not scorecard:
            return "Run Phase 2 intelligence to surface the primary roster weakness."
        weakest = min(
            scorecard.items(),
            key=lambda item: (
                1.0 - item[1] if item[0] in HIGHER_IS_WORSE_FIELDS else item[1]
            ),
        )[0]
        if (
            weakest == "flexibility"
            and starters is not None
            and players is not None
            and reserve is not None
            and taxi is not None
            and player_positions is not None
        ):
            flexibility_note = self._build_flexibility_note(
                starters, players, reserve, taxi, player_positions
            )
            if flexibility_note is not None:
                return flexibility_note
        return WEAKNESS_LABELS.get(
            weakest, "This roster needs more clarity before surfacing a weakness."
        )

    def _compute_delta(
        self,
        previous_state: dict[str, Any],
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        previous_players: dict[tuple[int, str], float] = {}
        for roster in previous_state.get("rosters", []):
            roster_id = int(roster.get("roster_id", 0))
            for value in roster.get("player_values", []):
                player_id = str(value.get("player_id"))
                lens_market = value.get("lens_market")
                if lens_market is not None:
                    previous_players[(roster_id, player_id)] = float(lens_market)

        current_players: dict[tuple[int, str], dict[str, Any]] = {}
        for roster in current_state.get("rosters", []):
            roster_id = int(roster.get("roster_id", 0))
            for value in roster.get("player_values", []):
                current_players[(roster_id, str(value.get("player_id")))] = value

        changed_players: list[dict[str, Any]] = []
        for key, payload in current_players.items():
            previous = previous_players.get(key)
            current = payload.get("lens_market")
            if previous is None or current is None:
                continue
            delta = round(float(current) - previous, 3)
            if abs(delta) < 0.01:
                continue
            changed_players.append(
                {
                    "roster_id": key[0],
                    "player_id": key[1],
                    "player_name": payload.get("player_name"),
                    "delta": delta,
                }
            )

        previous_rosters = {
            int(roster.get("roster_id", 0)): tuple(sorted(roster.get("players", [])))
            for roster in previous_state.get("rosters", [])
        }
        current_rosters = {
            int(roster.get("roster_id", 0)): tuple(sorted(roster.get("players", [])))
            for roster in current_state.get("rosters", [])
        }
        changed_rosters = [
            roster_id
            for roster_id, players in current_rosters.items()
            if players != previous_rosters.get(roster_id, ())
        ]

        return {
            "changed_players": sorted(
                changed_players,
                key=lambda item: abs(float(item["delta"])),
                reverse=True,
            )[:50],
            "changed_rosters": changed_rosters,
        }
