import pytest

from fantasy.ingestion.ingest_service import IngestService


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
