from fantasy.ingestion.sleeper_mapper import LeagueSettings, StandingRow
from fantasy.repositories.league_repo import LeagueRepo


def test_upsert_standings(db):
    repo = LeagueRepo(db)
    standing = StandingRow(
        league_id="test_league_001",
        roster_id=1,
        wins=8,
        losses=4,
        ties=0,
        fpts=120.5,
        fpts_against=111.2,
    )

    repo.upsert_standing(standing)
    updated = standing.model_copy(update={"fpts": 130.0})
    repo.upsert_standing(updated)

    count = db.execute("SELECT COUNT(*) FROM standings").fetchone()[0]
    fpts = db.execute(
        "SELECT fpts FROM standings WHERE league_id = ? AND roster_id = ?",
        ["test_league_001", 1],
    ).fetchone()[0]

    assert count == 1
    assert fpts == 130.0


def test_upsert_league(db):
    repo = LeagueRepo(db)
    league = LeagueSettings(
        league_id="test_league_001",
        name="Original",
        season="2025",
        scoring_settings={"rec": 1.0},
        roster_positions=["QB", "RB", "WR", "TE", "SUPER_FLEX"],
        settings_blob={"num_teams": 12},
        superflex=True,
        tep=False,
        ppr=1.0,
    )

    repo.upsert_league(league)
    repo.upsert_league(league.model_copy(update={"name": "Updated"}))

    count = db.execute("SELECT COUNT(*) FROM leagues").fetchone()[0]
    name = db.execute(
        "SELECT name FROM leagues WHERE league_id = ?", ["test_league_001"]
    ).fetchone()[0]

    assert count == 1
    assert name == "Updated"
