from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import duckdb

from fantasy.config import get_settings
from fantasy.portfolio.constants import (
    CORRELATED_RISK_MIN_LEAGUES,
    CORRELATED_RISK_MIN_PLAYERS,
)
from fantasy.portfolio.models import CorrelatedRiskPlayer, CorrelatedRiskRow, ExposureRow


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _valid_player_ids(values: list[Any]) -> list[str]:
    return [str(value) for value in values if value not in (None, "", 0, "0")]


class PortfolioRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _portfolio_owner_selection(self) -> tuple[str | None, bool]:
        settings = get_settings()

        if settings.PORTFOLIO_OWNER_ID:
            row = self._conn.execute(
                """
                SELECT owner_id
                FROM rosters
                WHERE owner_id = ?
                LIMIT 1
                """,
                [settings.PORTFOLIO_OWNER_ID],
            ).fetchone()
            return (str(row[0]), False) if row else (None, False)

        if settings.PORTFOLIO_OWNER_DISPLAY_NAME:
            row = self._conn.execute(
                """
                SELECT owner_id, COUNT(DISTINCT league_id) AS league_count
                FROM rosters
                WHERE owner_id IS NOT NULL
                  AND owner_display_name IS NOT NULL
                  AND lower(owner_display_name) = lower(?)
                GROUP BY owner_id
                ORDER BY league_count DESC, owner_id ASC
                LIMIT 1
                """,
                [settings.PORTFOLIO_OWNER_DISPLAY_NAME],
            ).fetchone()
            return (str(row[0]), False) if row else (None, False)

        row = self._conn.execute(
            """
            SELECT owner_id, COUNT(DISTINCT league_id) AS league_count
            FROM rosters
            WHERE owner_id IS NOT NULL
            GROUP BY owner_id
            ORDER BY league_count DESC, owner_id ASC
            LIMIT 1
            """
        ).fetchone()
        return (str(row[0]), True) if row else (None, True)

    def _portfolio_roster_rows(self) -> list[dict[str, Any]]:
        league_rows = self._conn.execute(
            """
            SELECT league_id
            FROM leagues
            ORDER BY name, league_id
            """
        ).fetchall()
        if not league_rows:
            return []

        owner_id, allow_fallback = self._portfolio_owner_selection()
        portfolio_rows: list[dict[str, Any]] = []
        for league_row in league_rows:
            league_id = str(league_row[0])
            roster = None
            if owner_id is not None:
                roster = self._conn.execute(
                    """
                    SELECT roster_id, players
                    FROM rosters
                    WHERE league_id = ? AND owner_id = ?
                    ORDER BY roster_id
                    LIMIT 1
                    """,
                    [league_id, owner_id],
                ).fetchone()
            if roster is None and allow_fallback:
                roster = self._conn.execute(
                    """
                    SELECT roster_id, players
                    FROM rosters
                    WHERE league_id = ?
                    ORDER BY roster_id
                    LIMIT 1
                    """,
                    [league_id],
                ).fetchone()
            if roster is None:
                continue

            portfolio_rows.append(
                {
                    "league_id": league_id,
                    "roster_id": int(roster[0]),
                    "players": _valid_player_ids(_loads(roster[1], [])),
                }
            )
        return portfolio_rows

    def _player_lookup(self, player_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not player_ids:
            return {}

        rows = self._conn.execute(
            """
            SELECT player_id, full_name, position, team
            FROM players
            WHERE player_id IN (SELECT UNNEST(?))
            """,
            [player_ids],
        ).fetchall()
        return {
            str(row[0]): {
                "full_name": str(row[1] or row[0]),
                "position": str(row[2] or "UNKNOWN"),
                "team": str(row[3]) if row[3] is not None else None,
            }
            for row in rows
        }

    def load_exposure_rows(self) -> list[ExposureRow]:
        roster_rows = self._portfolio_roster_rows()
        player_ids = sorted(
            {
                player_id
                for roster in roster_rows
                for player_id in roster["players"]
            }
        )
        player_lookup = self._player_lookup(player_ids)
        exposure: dict[str, dict[str, Any]] = {}

        for roster in roster_rows:
            league_id = str(roster["league_id"])
            seen_in_league: set[str] = set()
            for player_id in roster["players"]:
                if player_id in seen_in_league:
                    continue
                seen_in_league.add(player_id)
                lookup = player_lookup.get(
                    player_id,
                    {
                        "full_name": player_id,
                        "position": "UNKNOWN",
                        "team": None,
                    },
                )
                row = exposure.setdefault(
                    player_id,
                    {
                        "player_id": player_id,
                        "full_name": lookup["full_name"],
                        "position": lookup["position"],
                        "team": lookup["team"],
                        "owned_in_leagues": [],
                    },
                )
                row["owned_in_leagues"].append(league_id)

        results = [
            ExposureRow(
                player_id=payload["player_id"],
                full_name=payload["full_name"],
                position=payload["position"],
                team=payload["team"],
                owned_in_leagues=sorted(set(payload["owned_in_leagues"])),
                league_count=len(set(payload["owned_in_leagues"])),
            )
            for payload in exposure.values()
        ]
        results.sort(key=lambda row: (-row.league_count, row.full_name.lower(), row.player_id))
        return results

    def load_correlated_risk_rows(self) -> list[CorrelatedRiskRow]:
        roster_rows = self._portfolio_roster_rows()
        player_ids = sorted(
            {
                player_id
                for roster in roster_rows
                for player_id in roster["players"]
            }
        )
        player_lookup = self._player_lookup(player_ids)
        team_rows: dict[str, list[CorrelatedRiskPlayer]] = {}

        for roster in roster_rows:
            league_id = str(roster["league_id"])
            seen_in_league: set[str] = set()
            for player_id in roster["players"]:
                if player_id in seen_in_league:
                    continue
                seen_in_league.add(player_id)
                lookup = player_lookup.get(player_id)
                team = str(lookup["team"]).strip() if lookup and lookup["team"] is not None else ""
                if not team or team.upper() in {"UNKNOWN", "FA", "FREE AGENT"}:
                    continue
                team_rows.setdefault(team, []).append(
                    CorrelatedRiskPlayer(
                        player_id=player_id,
                        full_name=str(lookup["full_name"]),
                        league_id=league_id,
                    )
                )

        correlated_rows: list[CorrelatedRiskRow] = []
        for nfl_team, players in team_rows.items():
            unique_leagues = sorted({player.league_id for player in players})
            unique_players = {player.player_id for player in players}
            if len(unique_leagues) < CORRELATED_RISK_MIN_LEAGUES:
                continue
            if len(unique_players) < CORRELATED_RISK_MIN_PLAYERS:
                continue
            correlated_rows.append(
                CorrelatedRiskRow(
                    nfl_team=nfl_team,
                    players=sorted(players, key=lambda player: (player.full_name.lower(), player.league_id)),
                    league_ids=unique_leagues,
                )
            )

        correlated_rows.sort(
            key=lambda row: (-len(row.league_ids), -len({player.player_id for player in row.players}), row.nfl_team)
        )
        return correlated_rows

    def get_last_recalibration(self) -> datetime | None:
        try:
            row = self._conn.execute(
                "SELECT MAX(run_at) FROM retrospective_runs"
            ).fetchone()
        except duckdb.Error:
            return None
        if row is None or row[0] is None:
            return None
        return row[0]

    def save_retrospective_run(
        self,
        run_type: str,
        season: str,
        grades_json: dict[str, Any],
        notes: str | None = None,
    ) -> None:
        next_id = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM retrospective_runs"
        ).fetchone()
        self._conn.execute(
            """
            INSERT INTO retrospective_runs (id, run_type, season, grades_json, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                int(next_id[0] or 1),
                run_type,
                season,
                json.dumps(grades_json, separators=(",", ":")),
                notes,
            ],
        )
