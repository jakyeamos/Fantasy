from __future__ import annotations

import json
from typing import Any

import duckdb
import polars as pl

from fantasy.corrections.override_service import OverrideService
from fantasy.ingestion.gap_detector import GapDetector
from fantasy.ingestion.nfl_data_loader import SLEEPER_TO_NFLDATA_MAP
from fantasy.ingestion.sleeper_client import SleeperClient
from fantasy.ingestion.sleeper_mapper import SleeperMapper
from fantasy.repositories.league_repo import LeagueRepo
from fantasy.snapshots.snapshot_service import SnapshotService


class IngestService:
    def __init__(self, conn: duckdb.DuckDBPyConnection, client: SleeperClient):
        self.conn = conn
        self.client = client
        self.repo = LeagueRepo(conn)

    def _next_run_id(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM ingest_runs").fetchone()
        return int(row[0])

    def _get_latest_complete_cursor(self, league_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            SELECT cursor_json
            FROM ingest_runs
            WHERE league_id = ? AND status = 'complete'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            [league_id],
        ).fetchone()

        if row is None or row[0] is None:
            return {}

        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return {}

    def _normalize_player_record(
        self, player_id: str, raw_player: dict[str, Any] | None
    ) -> dict[str, Any]:
        raw_player = raw_player or {}
        full_name = (
            raw_player.get("full_name")
            or " ".join(
                part
                for part in [raw_player.get("first_name"), raw_player.get("last_name")]
                if part
            )
            or raw_player.get("search_full_name")
            or str(player_id)
        )
        return {
            **raw_player,
            "player_id": str(player_id),
            "full_name": full_name,
            "position": raw_player.get("position"),
            "team": raw_player.get("team"),
            "age": raw_player.get("age"),
        }

    async def _backfill_roster_players(self, rosters_raw: list[dict[str, Any]]) -> None:
        roster_player_ids = sorted(
            {
                str(player_id)
                for roster_raw in rosters_raw
                for player_id in (roster_raw.get("players") or [])
                if player_id not in (None, "", 0, "0")
            }
        )
        if not roster_player_ids:
            return

        existing_player_ids = {
            str(row[0])
            for row in self.conn.execute(
                """
                SELECT player_id
                FROM players
                WHERE player_id IN (
                    SELECT UNNEST(?)
                )
                """,
                [roster_player_ids],
            ).fetchall()
        }
        missing_player_ids = [
            player_id
            for player_id in roster_player_ids
            if player_id not in existing_player_ids
        ]
        if not missing_player_ids:
            return

        player_catalog: dict[str, dict[str, Any]] = {}
        fetch_players = getattr(self.client, "fetch_players", None)
        if callable(fetch_players):
            try:
                player_catalog = dict(await fetch_players())
            except Exception:
                player_catalog = {}

        for player_id in missing_player_ids:
            self.repo.upsert_player(
                self._normalize_player_record(player_id, player_catalog.get(player_id))
            )

    async def run(self, league_id: str, run_type: str = "full") -> int:
        running = self.conn.execute(
            "SELECT COUNT(*) FROM ingest_runs WHERE league_id = ? AND status = 'running'",
            [league_id],
        ).fetchone()[0]
        if running:
            raise RuntimeError(f"ingest already running for {league_id}")

        run_id = self._next_run_id()
        self.conn.execute(
            """
            INSERT INTO ingest_runs (id, league_id, run_type, status)
            VALUES (?, ?, ?, 'running')
            """,
            [run_id, league_id, run_type],
        )

        try:
            league_raw = await self.client.fetch_league(league_id)
            league = SleeperMapper.map_league(league_raw)
            self.repo.upsert_league(league)

            users_raw = await self.client.fetch_users(league_id)
            owner_display_names = {
                str(user.get("user_id")): str(
                    user.get("display_name")
                    or (user.get("metadata") or {}).get("team_name")
                    or user.get("username")
                    or user.get("user_id")
                )
                for user in users_raw
                if user.get("user_id") is not None
            }

            rosters_raw = await self.client.fetch_rosters(league_id)
            for roster_raw in rosters_raw:
                roster = SleeperMapper.map_roster(
                    {
                        **roster_raw,
                        "owner_display_name": owner_display_names.get(
                            str(roster_raw.get("owner_id"))
                        ),
                    }
                )
                self.repo.upsert_roster(roster, league_id)
                standing = SleeperMapper.map_standing(roster_raw, league_id)
                self.repo.upsert_standing(standing)
            await self._backfill_roster_players(rosters_raw)

            traded_picks_raw = await self.client.fetch_traded_picks(league_id)
            traded_picks = SleeperMapper.map_traded_picks(traded_picks_raw, league_id)
            self.repo.upsert_traded_picks(traded_picks)

            drafts_raw = await self.client.fetch_drafts(league_id)
            draft_slots = SleeperMapper.map_draft_slots(drafts_raw, league_id)
            self.repo.upsert_draft_slots(draft_slots)

            latest_cursor = self._get_latest_complete_cursor(league_id)
            state = await self.client.fetch_nfl_state()
            current_week = int(state.get("week", 18) or 18)

            if run_type == "incremental":
                start_week = int(latest_cursor.get("max_week_fetched", 0) or 0) + 1
            else:
                start_week = 1

            max_week_fetched = int(latest_cursor.get("max_week_fetched", 0) or 0)
            if start_week <= current_week:
                for week in range(start_week, current_week + 1):
                    transactions_raw = await self.client.fetch_transactions(league_id, week)
                    transactions = SleeperMapper.map_transactions(transactions_raw, league_id)
                    for txn in transactions:
                        self.repo.upsert_transaction(txn)
                    max_week_fetched = week

            override_service = OverrideService()
            override_service.apply_corrections(self.conn, league_id)

            season_number = int(league.season)
            season_rows = self.conn.execute(
                "SELECT season FROM player_stats_weekly WHERE season = ?",
                [season_number],
            ).fetchall()
            stats_df = pl.DataFrame(
                {"season": [int(row[0]) for row in season_rows]}
                if season_rows
                else {"season": []}
            )

            gaps = GapDetector.collect_all(
                conn=self.conn,
                league_id=league_id,
                scoring_settings=league.scoring_settings,
                sleeper_to_nfldata_map=SLEEPER_TO_NFLDATA_MAP,
                stats_df=stats_df,
                expected_years=[season_number],
            )

            cursor_json = json.dumps({"max_week_fetched": max_week_fetched})
            gaps_json = json.dumps([gap.model_dump() for gap in gaps])

            self.conn.execute(
                """
                UPDATE ingest_runs
                SET status = 'complete',
                    completed_at = CURRENT_TIMESTAMP,
                    cursor_json = ?,
                    gaps_json = ?,
                    error_message = NULL
                WHERE id = ?
                """,
                [cursor_json, gaps_json, run_id],
            )
            snapshot_service = SnapshotService(self.conn)
            snapshot_service.take_snapshot(
                [league_id], triggered_by="ingest", ingest_run_id=run_id
            )
            return run_id
        except Exception as exc:
            self.conn.execute(
                """
                UPDATE ingest_runs
                SET status = 'failed',
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = ?
                WHERE id = ?
                """,
                [str(exc), run_id],
            )
            raise
