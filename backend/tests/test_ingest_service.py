import pytest
import polars as pl
from unittest.mock import MagicMock, patch

from fantasy.ingestion.ingest_service import IngestService, _build_gsis_sleeper_map, _prepare_stats_df
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
    ):
        self._league = league
        self._rosters = rosters
        self._traded_picks = traded_picks
        self._weekly_transactions = weekly_transactions
        self._week = week
        self._users = users or []
        self._players = players or {}

    async def fetch_league(self, _league_id):
        return self._league

    async def fetch_rosters(self, _league_id):
        return self._rosters

    async def fetch_users(self, _league_id):
        return self._users

    async def fetch_traded_picks(self, _league_id):
        return self._traded_picks

    async def fetch_drafts(self, _league_id):
        return []

    async def fetch_players(self):
        return self._players

    async def fetch_transactions(self, _league_id, week):
        return self._weekly_transactions.get(week, [])

    async def fetch_nfl_state(self):
        return {"week": self._week, "season": "2025"}


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
        SELECT owner_id, owner_display_name
        FROM rosters
        WHERE league_id = 'test_league_001' AND roster_id = 1
        """
    ).fetchone()
    assert row == ("user_abc", "Display Alpha")


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


def test_build_gsis_sleeper_map_extracts_from_metadata_blob(db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
          ('4017', 'Player A', 'QB', 'SF', 26, '{"gsis_id": "00-0033873"}'),
          ('4663', 'Player B', 'WR', 'SF', 24, '{"gsis_id": "00-0036971"}'),
          ('9999', 'No GSIS',  'TE', 'X',  22, '{}')
        """
    )
    mapping = _build_gsis_sleeper_map(db)
    assert mapping == {"00-0033873": "4017", "00-0036971": "4663"}


def test_prepare_stats_df_remaps_ids_and_computes_fantasy_points():
    gsis_to_sleeper = {"00-0033873": "4017"}
    scoring = {"rec": 1.0, "rec_yd": 0.1}
    raw = pl.DataFrame(
        {
            "player_id": ["00-0033873", "00-0099999"],
            "player_name": ["Player A", "Unknown"],
            "position": ["WR", "WR"],
            "season": [2025, 2025],
            "week": [1, 1],
            "receptions": [6.0, 4.0],
            "targets": [8.0, 5.0],
            "receiving_yards": [80.0, 50.0],
            "receiving_tds": [0.0, 0.0],
            "rushing_yards": [0.0, 0.0],
            "rushing_tds": [0.0, 0.0],
            "carries": [0.0, 0.0],
            "passing_yards": [0.0, 0.0],
            "passing_tds": [0.0, 0.0],
            "interceptions": [0.0, 0.0],
            "passing_2pt_conversions": [0.0, 0.0],
            "receiving_2pt_conversions": [0.0, 0.0],
            "rushing_2pt_conversions": [0.0, 0.0],
            "fantasy_points": [None, None],
        }
    )
    result = _prepare_stats_df(raw, gsis_to_sleeper, scoring)
    assert result.height == 1, "unmapped player should be dropped"
    assert result["player_id"].to_list() == ["4017"]
    # 6 rec * 1.0 + 80 yards * 0.1 = 14.0
    assert result["fantasy_points"].to_list() == [14.0]
    assert result.columns == PLAYER_STATS_COLUMNS


@pytest.mark.asyncio
async def test_ingest_populates_player_stats_weekly(db, base_league, base_roster):
    stats_df = pl.DataFrame(
        {
            "player_id": ["00-0033873"],
            "player_name": ["Player One"],
            "position": ["WR"],
            "season": [2025],
            "week": [1],
            "receptions": [5.0],
            "targets": [7.0],
            "receiving_yards": [60.0],
            "receiving_tds": [0.0],
            "rushing_yards": [0.0],
            "rushing_tds": [0.0],
            "carries": [0.0],
            "passing_yards": [0.0],
            "passing_tds": [0.0],
            "interceptions": [0.0],
            "passing_2pt_conversions": [0.0],
            "receiving_2pt_conversions": [0.0],
            "rushing_2pt_conversions": [0.0],
            "fantasy_points": [None],
        }
    )
    db.execute(
        "INSERT INTO players (player_id, full_name, position, team, age, metadata_blob) "
        "VALUES ('4017', 'Player One', 'WR', 'SF', 24, '{\"gsis_id\": \"00-0033873\"}')"
    )
    from fantasy.ingestion.nfl_data_loader import NflDataPyLoader as RealLoader

    mock_loader = MagicMock()
    mock_loader.load_weekly_stats.return_value = stats_df
    mock_loader.upsert_weekly_stats.side_effect = RealLoader().upsert_weekly_stats

    with patch(
        "fantasy.ingestion.ingest_service.NflDataPyLoader", return_value=mock_loader
    ):
        client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)
        service = IngestService(db, client)
        await service.run("test_league_001", "full")

    rows = db.execute(
        "SELECT player_id, week, fantasy_points FROM player_stats_weekly"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "4017"
    assert rows[0][1] == 1
    assert rows[0][2] == pytest.approx(11.0)  # 5 rec * 1.0 + 60 yards * 0.1


@pytest.mark.asyncio
async def test_ingest_completes_when_stats_loader_raises(db, base_league, base_roster):
    mock_loader = MagicMock()
    mock_loader.load_weekly_stats.side_effect = RuntimeError("nfl_data_py unavailable")

    with patch(
        "fantasy.ingestion.ingest_service.NflDataPyLoader", return_value=mock_loader
    ):
        client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)
        service = IngestService(db, client)
        run_id = await service.run("test_league_001", "full")

    status = db.execute(
        "SELECT status FROM ingest_runs WHERE id = ?", [run_id]
    ).fetchone()[0]
    assert status == "complete"
