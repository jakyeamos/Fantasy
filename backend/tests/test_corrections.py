from fantasy.corrections.override_service import CorrectionCreate, OverrideService
from fantasy.ingestion.sleeper_mapper import LeagueSettings
from fantasy.repositories.league_repo import LeagueRepo


def test_correction_survives_reingest(db):
    service = OverrideService()
    repo = LeagueRepo(db)

    correction = service.create_correction(
        db,
        CorrectionCreate(
            league_id="test_league_001",
            entity_type="player",
            entity_id="4017",
            field="position",
            corrected_value="WR",
            original_value="RB",
        ),
    )

    repo.upsert_league(
        LeagueSettings(
            league_id="test_league_001",
            name="League",
            season="2025",
            scoring_settings={"rec": 1.0},
            roster_positions=["QB", "RB", "WR", "TE"],
            settings_blob={},
            superflex=False,
            tep=False,
            ppr=1.0,
        )
    )

    rows = db.execute(
        "SELECT COUNT(*) FROM corrections WHERE id = ?", [correction.id]
    ).fetchone()[0]
    assert rows == 1


def test_duplicate_correction_upserts(db):
    service = OverrideService()
    payload = CorrectionCreate(
        league_id="test_league_001",
        entity_type="player",
        entity_id="4017",
        field="position",
        corrected_value="WR",
        original_value="RB",
    )

    service.create_correction(db, payload)
    service.create_correction(db, payload.model_copy(update={"corrected_value": "TE"}))

    count = db.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
    value = db.execute("SELECT corrected_value FROM corrections").fetchone()[0]

    assert count == 1
    assert value == "TE"
