import json
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from fantasy.ingestion.ingest_service import IngestService
from fantasy.ingestion.nfl_data_loader import PLAYER_STATS_COLUMNS


class FakeSleeperClient:
    def __init__(
        self,
        league,
        rosters,
        traded_picks,
        weekly_transactions,
        week,
        users=None,
        players=None,
        drafts=None,
        draft_picks=None,
    ):
        self._league = league
        self._rosters = rosters
        self._traded_picks = traded_picks
        self._weekly_transactions = weekly_transactions
        self._week = week
        self._users = users or []
        self._players = players or {}
        self._drafts = drafts or []
        self._draft_picks = draft_picks or {}
        self._weekly_stats: dict[int, dict] = {}

    async def fetch_league(self, _league_id):
        return self._league

    async def fetch_rosters(self, _league_id):
        return self._rosters

    async def fetch_users(self, _league_id):
        return self._users

    async def fetch_traded_picks(self, _league_id):
        return self._traded_picks

    async def fetch_drafts(self, _league_id):
        return self._drafts

    async def fetch_draft_picks(self, draft_id):
        return self._draft_picks.get(draft_id, [])

    async def fetch_players(self):
        return self._players

    async def fetch_transactions(self, _league_id, week):
        return self._weekly_transactions.get(week, [])

    async def fetch_weekly_stats(self, _season_type, _season, week):
        return self._weekly_stats.get(week, {})

    async def fetch_nfl_state(self):
        return {"week": self._week, "season": "2025"}


class CatalogFailingSleeperClient(FakeSleeperClient):
    async def fetch_players(self):
        raise RuntimeError("player catalog unavailable")


@pytest.fixture
def base_roster():
    return {
        "roster_id": 1,
        "owner_id": "user_abc",
        "league_id": "test_league_001",
        "starters": ["4017", "4663"],
        "players": ["4017", "4663", "2374", "6945"],
        "reserve": [],
        "taxi": [],
        "settings": {
            "wins": 8,
            "losses": 5,
            "ties": 0,
            "fpts": 1500,
            "fpts_decimal": 0,
            "fpts_against": 1480.3,
        },
    }


@pytest.fixture
def base_league():
    return {
        "league_id": "test_league_001",
        "name": "Test League",
        "season": "2025",
        "scoring_settings": {"rec": 1.0, "rec_yd": 0.1},
        "roster_positions": ["QB", "RB", "WR", "TE", "SUPER_FLEX"],
        "settings": {"num_teams": 12},
    }


def _txn(txn_id, txn_type, week):
    return {
        "transaction_id": txn_id,
        "type": txn_type,
        "status": "complete",
        "created": 1700000000000 + week,
        "roster_ids": [1, 2],
        "adds": {"4017": 2},
        "drops": {"2374": 1},
        "draft_picks": [],
        "settings": {"waiver_bid": 17} if txn_type == "waiver" else {},
        "leg": week,
    }


@pytest.mark.asyncio
async def test_trade_history_all_weeks(db, base_league, base_roster):
    weekly_transactions = {
        1: [_txn("trade_1", "trade", 1)],
        5: [_txn("trade_5", "trade", 5)],
        12: [_txn("trade_12", "trade", 12)],
    }
    client = FakeSleeperClient(base_league, [base_roster], [], weekly_transactions, week=12)

    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    count = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE type = 'trade'"
    ).fetchone()[0]
    assert count == 3


@pytest.mark.asyncio
async def test_transactions_by_type(db, base_league, base_roster):
    weekly_transactions = {
        1: [_txn("trade_1", "trade", 1), _txn("fa_1", "free_agent", 1)],
    }
    client = FakeSleeperClient(base_league, [base_roster], [], weekly_transactions, week=1)

    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    types = {
        row[0]
        for row in db.execute("SELECT DISTINCT type FROM transactions ORDER BY type").fetchall()
    }
    assert "trade" in types
    assert "free_agent" in types


@pytest.mark.asyncio
async def test_idempotent_ingest(db, base_league, base_roster):
    weekly_transactions = {
        1: [_txn("trade_1", "trade", 1), _txn("fa_1", "free_agent", 1)],
        2: [_txn("waiver_1", "waiver", 2)],
    }
    client = FakeSleeperClient(base_league, [base_roster], [], weekly_transactions, week=2)

    service = IngestService(db, client)
    await service.run("test_league_001", "full")
    first_count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    await service.run("test_league_001", "full")
    second_count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    assert first_count == second_count


@pytest.mark.asyncio
async def test_ingest_persists_owner_display_names(db, base_league, base_roster):
    client = FakeSleeperClient(
        base_league,
        [base_roster],
        [],
        {},
        week=1,
        users=[
            {
                "user_id": "user_abc",
                "display_name": "Display Alpha",
                "username": "alpha",
                "metadata": {"team_name": "Alpha Team"},
            }
        ],
    )

    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    row = db.execute(
        """
        SELECT owner_id, owner_display_name, waiver_position, waiver_budget_used
        FROM rosters
        WHERE league_id = 'test_league_001' AND roster_id = 1
        """
    ).fetchone()
    assert row == ("user_abc", "Display Alpha", None, None)


@pytest.mark.asyncio
async def test_ingest_persists_waiver_fields(db, base_league, base_roster):
    roster = {
        **base_roster,
        "settings": {
            **base_roster["settings"],
            "waiver_position": 2,
            "waiver_budget_used": 41,
        },
    }
    weekly_transactions = {
        1: [_txn("waiver_1", "waiver", 1)],
    }
    client = FakeSleeperClient(base_league, [roster], [], weekly_transactions, week=1)

    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    roster_row = db.execute(
        """
        SELECT waiver_position, waiver_budget_used
        FROM rosters
        WHERE league_id = 'test_league_001' AND roster_id = 1
        """
    ).fetchone()
    transaction_row = db.execute(
        """
        SELECT waiver_bid
        FROM transactions
        WHERE transaction_id = 'waiver_1'
        """
    ).fetchone()

    assert roster_row == (2, 41)
    assert transaction_row == (17,)


@pytest.mark.asyncio
async def test_ingest_persists_draft_pick_selections(db, base_league, base_roster):
    client = FakeSleeperClient(
        base_league,
        [base_roster],
        [],
        {},
        week=1,
        drafts=[
            {
                "draft_id": "draft_2025",
                "season": "2025",
                "type": "linear",
                "status": "complete",
                "metadata": {"name": "2025 Rookie Draft"},
                "settings": {"rounds": 3, "teams": 12},
                "slot_to_roster_id": {"1": 1},
            }
        ],
        draft_picks={
            "draft_2025": [
                {
                    "roster_id": 1,
                    "player_id": "4017",
                    "pick_no": 1,
                    "round": 1,
                    "metadata": {"position": "QB"},
                }
            ]
        },
    )

    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    row = db.execute(
        """
        SELECT league_id, draft_id, roster_id, player_id, pick_slot, round_number, season, draft_type, position
        FROM draft_pick_selections
        """
    ).fetchone()
    assert row == (
        "test_league_001",
        "draft_2025",
        1,
        "4017",
        1,
        1,
        2025,
        "rookie",
        "QB",
    )


@pytest.mark.asyncio
async def test_ingest_backfills_roster_players(db, base_league, base_roster):
    client = FakeSleeperClient(
        base_league,
        [base_roster],
        [],
        {},
        week=1,
        players={
            "4017": {
                "player_id": "4017",
                "full_name": "Player One",
                "position": "QB",
                "team": "AAA",
                "age": 25,
            },
            "4663": {
                "player_id": "4663",
                "first_name": "Player",
                "last_name": "Two",
                "position": "RB",
                "team": "BBB",
                "age": 24,
            },
        },
    )

    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    rows = db.execute(
        """
        SELECT player_id, full_name, position
        FROM players
        ORDER BY player_id
        """
    ).fetchall()
    assert rows == [
        ("2374", "2374", None),
        ("4017", "Player One", "QB"),
        ("4663", "Player Two", "RB"),
        ("6945", "6945", None),
    ]


@pytest.mark.asyncio
async def test_ingest_records_player_backfill_catalog_degradation(
    db,
    base_league,
    base_roster,
    caplog,
):
    client = CatalogFailingSleeperClient(
        base_league,
        [base_roster],
        [],
        {},
        week=1,
    )

    service = IngestService(db, client)
    run_id = await service.run("test_league_001", "full")

    cursor_json = db.execute(
        "SELECT cursor_json FROM ingest_runs WHERE id = ?",
        [run_id],
    ).fetchone()[0]
    assert "player_backfill_catalog_unavailable" in cursor_json
    assert "player catalog unavailable" in cursor_json
    assert any(
        "player backfill catalog unavailable" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_ingest_populates_player_stats_weekly(db, base_league, base_roster):
    db.execute(
        "INSERT INTO players (player_id, full_name, position, team, age, metadata_blob) "
        "VALUES ('4017', 'Player One', 'WR', 'SF', 24, '{}')"
    )
    client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)
    client._weekly_stats = {
        1: {"4017": {"rec": 5.0, "rec_yd": 60.0}}
    }
    service = IngestService(db, client)
    await service.run("test_league_001", "full")

    rows = db.execute(
        "SELECT player_id, week, fantasy_points FROM player_stats_weekly"
    ).fetchall()
    # Only 4017 is in players table; stats for all Sleeper IDs in response are stored
    matching = [r for r in rows if r[0] == "4017"]
    assert len(matching) == 1
    assert matching[0][1] == 1
    assert matching[0][2] == pytest.approx(11.0)  # 5 rec * 1.0 + 60 yards * 0.1


@pytest.mark.asyncio
async def test_ingest_completes_when_stats_fetch_raises(db, base_league, base_roster):
    client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)

    original_fetch = client.fetch_weekly_stats

    async def raising_fetch(*args, **kwargs):
        raise RuntimeError("stats endpoint unavailable")

    client.fetch_weekly_stats = raising_fetch
    service = IngestService(db, client)
    run_id = await service.run("test_league_001", "full")

    status = db.execute(
        "SELECT status FROM ingest_runs WHERE id = ?", [run_id]
    ).fetchone()[0]
    assert status == "complete"
    gaps = db.execute(
        "SELECT gaps_json FROM ingest_runs WHERE id = ?", [run_id]
    ).fetchone()[0]
    assert "Missing Sleeper Weekly Stats" in gaps
    assert "weekly_stats_fetch_failed" in db.execute(
        "SELECT cursor_json FROM ingest_runs WHERE id = ?", [run_id]
    ).fetchone()[0]
    assert db.execute(
        """
        SELECT COUNT(*)
        FROM freshness_domains
        WHERE league_id = 'test_league_001' AND domain IN ('stats', 'usage')
        """
    ).fetchone()[0] == 0


@pytest.mark.asyncio
async def test_preseason_ingest_validates_prior_season_and_marks_stats_fresh(
    db, base_league, base_roster
):
    preseason_league = {**base_league, "season": "2026"}
    client = FakeSleeperClient(
        preseason_league, [base_roster], [], {}, week=0
    )

    async def fetch_preseason_state():
        return {"season_type": "pre", "season": "2026", "week": 0}

    client.fetch_nfl_state = fetch_preseason_state
    client._weekly_stats = {
        week: {"4017": {"rec": 5.0, "rec_yd": 60.0}}
        for week in range(1, 19)
    }

    service = IngestService(db, client)
    run_id = await service.run("test_league_001", "full")

    gaps = db.execute(
        "SELECT gaps_json FROM ingest_runs WHERE id = ?", [run_id]
    ).fetchone()[0]
    assert "2026 Season Stats" not in gaps
    assert "Unmapped Scoring Key" not in gaps
    assert db.execute(
        "SELECT COUNT(*) FROM player_stats_weekly WHERE season = 2025"
    ).fetchone()[0] == 18
    freshness = db.execute(
        """
        SELECT domain
        FROM freshness_domains
        WHERE league_id = 'test_league_001' AND domain IN ('stats', 'usage')
        ORDER BY domain
        """
    ).fetchall()
    assert freshness == [("stats",), ("usage",)]


def test_stats_integrity_repair_removes_only_proven_current_season_clone(
    db,
    base_league,
    base_roster,
):
    rows = [
        (
            f"player_{player}",
            f"Player {player}",
            "WR",
            season,
            1,
            10.0,
            5.0,
            1.0,
            0.0,
            50.0,
            5.0,
        )
        for season in (2025, 2026)
        for player in range(100)
    ]
    db.executemany(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points,
            targets, carries, passing_yards, receiving_yards, rushing_yards
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    service = IngestService(
        db,
        FakeSleeperClient(base_league, [base_roster], [], {}, week=0),
    )

    actions = service._repair_stats_integrity(
        league_season=2026,
        stats_season=2025,
        season_type="pre",
        stats_max_week=18,
    )

    assert actions == [
        {
            "action": "removed_cross_season_clone",
            "season": 2026,
            "compared_with": 2025,
            "rows_removed": 100,
        }
    ]
    assert db.execute(
        "SELECT COUNT(*) FROM player_stats_weekly WHERE season = 2026"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM player_stats_weekly WHERE season = 2025"
    ).fetchone()[0] == 100


def test_stats_integrity_repair_removes_impossible_future_regular_weeks(
    db,
    base_league,
    base_roster,
):
    db.executemany(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, fantasy_points
        ) VALUES ('player_1', 'Player 1', 'WR', 2026, ?, ?)
        """,
        [(1, 10.0), (2, 20.0), (3, 30.0)],
    )
    service = IngestService(
        db,
        FakeSleeperClient(base_league, [base_roster], [], {}, week=1),
    )

    actions = service._repair_stats_integrity(
        league_season=2026,
        stats_season=2026,
        season_type="regular",
        stats_max_week=1,
    )

    assert actions == [
        {
            "action": "removed_future_regular_weeks",
            "season": 2026,
            "after_week": 1,
            "rows_removed": 2,
        }
    ]
    assert db.execute(
        "SELECT week FROM player_stats_weekly WHERE season = 2026 ORDER BY week"
    ).fetchall() == [(1,)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prior_cursor",
    [
        {"stats_season": 2025, "max_week_fetched": 18},
        {"max_week_fetched": 18},
    ],
    ids=["prior-season", "legacy-week-only"],
)
async def test_incremental_ingest_resets_week_cursor_when_stats_season_changes(
    db,
    base_league,
    base_roster,
    prior_cursor,
):
    db.execute(
        """
        INSERT INTO ingest_runs (id, league_id, run_type, status, cursor_json)
        VALUES (90, 'test_league_001', 'incremental', 'complete', ?)
        """,
        [json.dumps(prior_cursor)],
    )
    regular_league = {**base_league, "season": "2026"}
    client = FakeSleeperClient(regular_league, [base_roster], [], {}, week=1)
    client._weekly_stats = {1: {"4017": {"rec": 5.0, "rec_yd": 60.0}}}

    service = IngestService(db, client)
    run_id = await service.run("test_league_001", "incremental")

    cursor = json.loads(
        db.execute(
            "SELECT cursor_json FROM ingest_runs WHERE id = ?", [run_id]
        ).fetchone()[0]
    )
    assert cursor["stats_season"] == 2026
    assert cursor["max_week_fetched"] == 1
    assert db.execute(
        "SELECT COUNT(*) FROM player_stats_weekly WHERE season = 2026"
    ).fetchone()[0] == 1


@pytest.mark.asyncio
async def test_incremental_cursor_does_not_advance_past_empty_stats_week(
    db,
    base_league,
    base_roster,
):
    db.execute(
        """
        INSERT INTO ingest_runs (id, league_id, run_type, status, cursor_json)
        VALUES (90, 'test_league_001', 'incremental', 'complete', ?)
        """,
        [json.dumps({"stats_season": 2025, "max_week_fetched": 0})],
    )
    client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)

    service = IngestService(db, client)
    run_id = await service.run("test_league_001", "incremental")

    cursor = json.loads(
        db.execute(
            "SELECT cursor_json FROM ingest_runs WHERE id = ?", [run_id]
        ).fetchone()[0]
    )
    assert cursor["stats_season"] == 2025
    assert cursor["max_week_fetched"] == 0
