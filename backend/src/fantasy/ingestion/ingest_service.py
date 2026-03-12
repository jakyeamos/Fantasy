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

            rosters_raw = await self.client.fetch_rosters(league_id)
            for roster_raw in rosters_raw:
                roster = SleeperMapper.map_roster(roster_raw)
                self.repo.upsert_roster(roster, league_id)
                standing = SleeperMapper.map_standing(roster_raw, league_id)
                self.repo.upsert_standing(standing)

            traded_picks_raw = await self.client.fetch_traded_picks(league_id)
            traded_picks = SleeperMapper.map_traded_picks(traded_picks_raw)
            self.repo.upsert_traded_picks(traded_picks)

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
