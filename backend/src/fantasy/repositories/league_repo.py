from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.ingestion.sleeper_mapper import (
    DraftSlot,
    LeagueSettings,
    RosterSnapshot,
    StandingRow,
    TradedPick,
    TransactionRecord,
)


def _dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


class LeagueRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def _next_id(self, table: str) -> int:
        return int(self.conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0])

    def upsert_league(self, league: LeagueSettings) -> None:
        self.conn.execute(
            """
            INSERT INTO leagues (
                league_id, name, season, scoring_settings, roster_positions,
                settings_blob, superflex, tep, ppr
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id) DO UPDATE SET
                name = EXCLUDED.name,
                season = EXCLUDED.season,
                scoring_settings = EXCLUDED.scoring_settings,
                roster_positions = EXCLUDED.roster_positions,
                settings_blob = EXCLUDED.settings_blob,
                superflex = EXCLUDED.superflex,
                tep = EXCLUDED.tep,
                ppr = EXCLUDED.ppr
            """,
            [
                league.league_id,
                league.name,
                league.season,
                _dumps(league.scoring_settings),
                _dumps(league.roster_positions),
                _dumps(league.settings_blob),
                league.superflex,
                league.tep,
                league.ppr,
            ],
        )

    def upsert_roster(self, roster: RosterSnapshot, league_id: str) -> None:
        existing = self.conn.execute(
            "SELECT id FROM rosters WHERE league_id = ? AND roster_id = ?",
            [league_id, roster.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("rosters")

        self.conn.execute(
            """
            INSERT INTO rosters (
                id, league_id, roster_id, owner_id, owner_display_name,
                waiver_position, waiver_budget_used, starters, players, reserve, taxi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                owner_id = EXCLUDED.owner_id,
                owner_display_name = EXCLUDED.owner_display_name,
                waiver_position = EXCLUDED.waiver_position,
                waiver_budget_used = EXCLUDED.waiver_budget_used,
                starters = EXCLUDED.starters,
                players = EXCLUDED.players,
                reserve = EXCLUDED.reserve,
                taxi = EXCLUDED.taxi
            """,
            [
                row_id,
                league_id,
                roster.roster_id,
                roster.owner_id,
                roster.owner_display_name,
                roster.waiver_position,
                roster.waiver_budget_used,
                _dumps(roster.starters),
                _dumps(roster.starters + roster.bench + roster.ir + roster.taxi),
                _dumps(roster.ir),
                _dumps(roster.taxi),
            ],
        )

    def upsert_standing(self, standing: StandingRow) -> None:
        existing = self.conn.execute(
            "SELECT id FROM standings WHERE league_id = ? AND roster_id = ?",
            [standing.league_id, standing.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("standings")

        self.conn.execute(
            """
            INSERT INTO standings (
                id, league_id, roster_id, wins, losses, ties, fpts, fpts_against
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                wins = EXCLUDED.wins,
                losses = EXCLUDED.losses,
                ties = EXCLUDED.ties,
                fpts = EXCLUDED.fpts,
                fpts_against = EXCLUDED.fpts_against
            """,
            [
                row_id,
                standing.league_id,
                standing.roster_id,
                standing.wins,
                standing.losses,
                standing.ties,
                standing.fpts,
                standing.fpts_against,
            ],
        )

    def upsert_traded_picks(self, picks: list[TradedPick]) -> None:
        for pick in picks:
            existing = self.conn.execute(
                """
                SELECT id
                FROM traded_picks
                WHERE league_id = ? AND season = ? AND round = ? AND roster_id = ?
                """,
                [pick.league_id, pick.season, pick.round, pick.roster_id],
            ).fetchone()
            row_id = int(existing[0]) if existing else self._next_id("traded_picks")

            self.conn.execute(
                """
                INSERT INTO traded_picks (
                    id, league_id, season, round, roster_id, owner_id, previous_owner_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (league_id, season, round, roster_id) DO UPDATE SET
                    owner_id = EXCLUDED.owner_id,
                    previous_owner_id = EXCLUDED.previous_owner_id
                """,
                [
                    row_id,
                    pick.league_id,
                    pick.season,
                    pick.round,
                    pick.roster_id,
                    str(pick.owner_id),
                    str(pick.previous_owner_id) if pick.previous_owner_id is not None else None,
                ],
            )

    def upsert_draft_slots(self, slots: list[DraftSlot]) -> None:
        for slot in slots:
            existing = self.conn.execute(
                """
                SELECT id FROM draft_slots
                WHERE league_id = ? AND draft_id = ? AND roster_id = ?
                """,
                [slot.league_id, slot.draft_id, slot.roster_id],
            ).fetchone()
            row_id = int(existing[0]) if existing else self._next_id("draft_slots")
            self.conn.execute(
                """
                INSERT INTO draft_slots (
                    id, league_id, draft_id, season, roster_id, confirmed_slot, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (league_id, draft_id, roster_id) DO UPDATE SET
                    confirmed_slot = EXCLUDED.confirmed_slot,
                    status = EXCLUDED.status,
                    ingested_at = CURRENT_TIMESTAMP
                """,
                [
                    row_id,
                    slot.league_id,
                    slot.draft_id,
                    slot.season,
                    slot.roster_id,
                    slot.confirmed_slot,
                    slot.status,
                ],
            )

    def upsert_player(self, player_dict: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (player_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                position = EXCLUDED.position,
                team = EXCLUDED.team,
                age = EXCLUDED.age,
                metadata_blob = EXCLUDED.metadata_blob
            """,
            [
                player_dict.get("player_id"),
                player_dict.get("full_name"),
                player_dict.get("position"),
                player_dict.get("team"),
                player_dict.get("age"),
                _dumps(player_dict),
            ],
        )

    def upsert_transaction(self, txn: TransactionRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO transactions (
                transaction_id,
                league_id,
                type,
                status,
                created_at,
                roster_ids,
                adds,
                drops,
                draft_picks,
                waiver_bid,
                week
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (transaction_id) DO UPDATE SET
                status = EXCLUDED.status,
                type = EXCLUDED.type,
                created_at = EXCLUDED.created_at,
                roster_ids = EXCLUDED.roster_ids,
                adds = EXCLUDED.adds,
                drops = EXCLUDED.drops,
                draft_picks = EXCLUDED.draft_picks,
                waiver_bid = EXCLUDED.waiver_bid,
                week = EXCLUDED.week
            """,
            [
                txn.transaction_id,
                txn.league_id,
                txn.type,
                txn.status,
                txn.created_at,
                _dumps(txn.roster_ids),
                _dumps(txn.adds),
                _dumps(txn.drops),
                _dumps(txn.draft_picks),
                txn.waiver_bid,
                txn.week,
            ],
        )
