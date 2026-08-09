from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import duckdb
import polars as pl

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.corrections.override_service import OverrideService
from fantasy.ingestion.gap_detector import GapDetector
from fantasy.ingestion.nfl_data_loader import NflDataPyLoader, build_sleeper_stats_df
from fantasy.ingestion.sleeper_client import SleeperClient
from fantasy.ingestion.sleeper_mapper import SleeperMapper
from fantasy.repositories.league_repo import LeagueRepo
from fantasy.intelligence.intelligence_service import IntelligenceService
from fantasy.profiling.profiling_engine import ProfilingEngine
from fantasy.rookie_pick.rookie_pick_engine import RookiePickProfileEngine
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo
from fantasy.snapshots.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self, conn: duckdb.DuckDBPyConnection, client: SleeperClient):
        self.conn = conn
        self.client = client
        self.repo = LeagueRepo(conn)
        self.degradation_warnings: list[str] = []

    def _record_degradation(self, warning: str) -> None:
        self.degradation_warnings.append(warning)
        logger.warning(warning.replace("_", " "))

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
        global_freshness = ContextRepo(self.conn).get_freshness_rows(
            "__global__", ["player_metadata"]
        ).get("player_metadata")
        catalog_fetch_due = (
            global_freshness is None
            or global_freshness.fetched_at is None
            or datetime.now(timezone.utc)
            - global_freshness.fetched_at.replace(tzinfo=timezone.utc)
            >= timedelta(hours=24)
        )
        if callable(fetch_players) and catalog_fetch_due:
            try:
                player_catalog = dict(await fetch_players())
                for catalog_player_id, raw_player in player_catalog.items():
                    self.repo.upsert_player(
                        self._normalize_player_record(
                            str(catalog_player_id), raw_player
                        )
                    )
                FreshnessService(ContextRepo(self.conn)).mark_source_result(
                    league_id="__global__",
                    domain="player_metadata",
                    source_id="sleeper:players_nfl",
                    parsed_successfully=bool(player_catalog),
                    record_count=len(player_catalog),
                    notes="Sleeper player catalog fetch (limited to once daily).",
                )
            except Exception as exc:
                player_catalog = {}
                FreshnessService(ContextRepo(self.conn)).mark_source_result(
                    league_id="__global__",
                    domain="player_metadata",
                    source_id="sleeper:players_nfl",
                    parsed_successfully=False,
                    record_count=0,
                    notes=str(exc),
                )
                self._record_degradation(
                    "player_backfill_catalog_unavailable: "
                    f"{len(missing_player_ids)} roster player(s) missing from local players table; "
                    f"using ID-only placeholders because Sleeper player catalog fetch failed: {exc}"
                )
        elif not catalog_fetch_due:
            self._record_degradation(
                "player_backfill_catalog_daily_limit: Sleeper player metadata was already fetched "
                "within 24 hours; unresolved players use local placeholders until the next window."
            )

        placeholder_player_ids = [
            player_id for player_id in missing_player_ids if player_id not in player_catalog
        ]
        if placeholder_player_ids:
            self._record_degradation(
                "player_backfill_placeholders: "
                f"{len(placeholder_player_ids)} roster player(s) inserted with ID-only metadata; "
                "rerun ingest after the Sleeper player catalog is available."
            )

        for player_id in missing_player_ids:
            self.repo.upsert_player(
                self._normalize_player_record(player_id, player_catalog.get(player_id))
            )

    def _infer_draft_type(
        self,
        draft: dict[str, Any],
        raw_picks: list[dict[str, Any]],
    ) -> str:
        metadata = draft.get("metadata") if isinstance(draft.get("metadata"), dict) else {}
        settings = draft.get("settings") if isinstance(draft.get("settings"), dict) else {}
        searchable = " ".join(
            str(value).lower()
            for value in [
                draft.get("draft_type"),
                draft.get("type"),
                draft.get("name"),
                metadata.get("name"),
                metadata.get("description"),
            ]
            if value is not None
        )
        if "rookie" in searchable:
            return "rookie"
        if "startup" in searchable or "start-up" in searchable:
            return "startup"

        rounds = settings.get("rounds") or draft.get("rounds")
        teams = settings.get("teams") or draft.get("teams")
        try:
            round_count = int(rounds)
            team_count = int(teams)
        except (TypeError, ValueError):
            round_count = 0
            team_count = 0
        if round_count and round_count <= 8:
            return "rookie"
        if team_count and raw_picks and len(raw_picks) <= team_count * 8:
            return "rookie"
        return "startup"

    async def _store_draft_pick_selections(
        self, league_id: str, drafts_raw: list[dict[str, Any]]
    ) -> dict[str, int]:
        rookie_pick_repo = RookiePickRepo(self.conn)
        processed_drafts = 0
        processed_selections = 0

        for draft in drafts_raw:
            draft_id = draft.get("draft_id")
            season = draft.get("season")
            if draft_id is None or season is None:
                continue
            raw_picks = await self.client.fetch_draft_picks(str(draft_id))
            if not raw_picks:
                continue
            draft_type = self._infer_draft_type(draft, raw_picks)
            selections = SleeperMapper.map_draft_pick_selections(
                raw_picks,
                league_id,
                str(draft_id),
                int(season),
                draft_type,
            )
            for selection in selections:
                rookie_pick_repo.upsert_draft_selection(selection)
            processed_drafts += 1
            processed_selections += len(selections)

        engine = RookiePickProfileEngine(self.conn)
        enriched = engine.enrich_selection_archetypes(league_id)
        roster_rows = self.conn.execute(
            """
            SELECT roster_id
            FROM rosters
            WHERE league_id = ?
            ORDER BY roster_id
            """,
            [league_id],
        ).fetchall()
        for row in roster_rows:
            engine.compute_profile(league_id, int(row[0]))

        freshness = FreshnessService(repo=ContextRepo(self.conn))
        freshness.mark_refreshed(league_id, "draft_capital")
        freshness.mark_refreshed(league_id, "landing_spots")

        return {
            "drafts": processed_drafts,
            "selections": processed_selections,
            "enriched": enriched,
            "profiles": len(roster_rows),
        }

    async def ingest_draft_picks(self, league_id: str) -> dict[str, int]:
        drafts_raw = await self.client.fetch_drafts(league_id)
        return await self._store_draft_pick_selections(league_id, drafts_raw)

    async def run(self, league_id: str, run_type: str = "full") -> int:
        self.degradation_warnings = []
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
            print(f"[ingest:{run_id}] fetching league {league_id}...")
            league_raw = await self.client.fetch_league(league_id)
            league = SleeperMapper.map_league(league_raw)
            self.repo.upsert_league(league)

            print(f"[ingest:{run_id}] fetching users...")
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

            print(f"[ingest:{run_id}] fetching rosters...")
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

            print(f"[ingest:{run_id}] fetching traded picks...")
            traded_picks_raw = await self.client.fetch_traded_picks(league_id)
            traded_picks = SleeperMapper.map_traded_picks(traded_picks_raw, league_id)
            self.repo.upsert_traded_picks(traded_picks)

            print(f"[ingest:{run_id}] fetching drafts...")
            drafts_raw = await self.client.fetch_drafts(league_id)
            draft_slots = SleeperMapper.map_draft_slots(drafts_raw, league_id)
            self.repo.upsert_draft_slots(draft_slots)
            draft_selection_summary = await self._store_draft_pick_selections(
                league_id, drafts_raw
            )
            print(
                f"[ingest:{run_id}]   draft selections loaded: "
                f"{draft_selection_summary['selections']}"
            )

            print(f"[ingest:{run_id}] fetching NFL state...")
            latest_cursor = self._get_latest_complete_cursor(league_id)
            state = await self.client.fetch_nfl_state()
            season_type = str(state.get("season_type") or "regular")
            current_week = int(state.get("week", 18) or 18)

            # In the offseason/preseason Sleeper rolls the season counter forward
            # but the last completed season's stats live under (season - 1).
            season_number = int(league.season)
            if season_type in ("off", "pre"):
                stats_season = season_number - 1
                stats_max_week = 18
            else:
                stats_season = season_number
                stats_max_week = current_week

            print(f"[ingest:{run_id}]   NFL state: season={state.get('season')} season_type={season_type} week={current_week} stats_season={stats_season}")

            if run_type == "incremental":
                start_week = int(latest_cursor.get("max_week_fetched", 0) or 0) + 1
            else:
                start_week = 1
            all_weeks_stats: dict[int, dict[str, dict]] = {}
            max_week_fetched = int(latest_cursor.get("max_week_fetched", 0) or 0)
            if start_week <= stats_max_week:
                print(f"[ingest:{run_id}] fetching weeks {start_week}–{stats_max_week} season={stats_season} (transactions + stats)...")
                for week in range(start_week, stats_max_week + 1):
                    print(f"[ingest:{run_id}]   week {week}/{stats_max_week}")
                    transactions_raw = await self.client.fetch_transactions(league_id, week)
                    transactions = SleeperMapper.map_transactions(transactions_raw, league_id)
                    for txn in transactions:
                        self.repo.upsert_transaction(txn)
                    try:
                        week_stats = await self.client.fetch_weekly_stats(
                            "regular", stats_season, week
                        )
                        all_weeks_stats[week] = week_stats
                        print(f"[ingest:{run_id}]     stats players loaded: {len(week_stats)}")
                    except Exception as stats_exc:
                        print(f"[ingest:{run_id}]     WARNING: stats fetch failed for week {week}: {stats_exc}")
                    max_week_fetched = week

            print(f"[ingest:{run_id}] applying corrections...")
            override_service = OverrideService()
            override_service.apply_corrections(self.conn, league_id)

            # Load weekly stats using Sleeper IDs directly — no GSIS translation needed
            print(f"[ingest:{run_id}] loading weekly stats ({len(all_weeks_stats)} weeks with data)...")
            if all_weeks_stats:
                player_info = {
                    str(row[0]): (str(row[1]), str(row[2]))
                    for row in self.conn.execute(
                        "SELECT player_id, COALESCE(full_name, player_id), COALESCE(position, '') FROM players"
                    ).fetchall()
                }
                stats_df_full = build_sleeper_stats_df(
                    all_weeks_stats, league.scoring_settings, stats_season, player_info
                )
                loader = NflDataPyLoader()
                loader.upsert_weekly_stats(self.conn, stats_df_full)
                print(f"[ingest:{run_id}]   upserted {stats_df_full.height} player-week rows")

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
                sleeper_to_nfldata_map={},
                stats_df=stats_df,
                expected_years=[season_number],
            )

            cursor_json = json.dumps(
                {
                    "max_week_fetched": max_week_fetched,
                    "degradation_warnings": self.degradation_warnings,
                }
            )
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
            print(f"[ingest:{run_id}] taking snapshot...")
            snapshot_service = SnapshotService(self.conn)
            snapshot_service.take_snapshot(
                [league_id], triggered_by="ingest", ingest_run_id=run_id
            )
            print(f"[ingest:{run_id}] computing profiles...")
            ProfilingEngine(self.conn).compute_all_profiles(league_id)
            print(f"[ingest:{run_id}] computing intelligence...")
            IntelligenceService(self.conn).compute_league(league_id)
            print(f"[ingest:{run_id}] done.")
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
