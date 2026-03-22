from fantasy.intelligence.intelligence_service import IntelligenceService


def test_idempotent_compute(phase2_seed_data):
    service = IntelligenceService(phase2_seed_data)
    first = service.compute_league("league_x")
    second = service.compute_league("league_x")
    assert first["scorecards"][1].model_dump() == second["scorecards"][1].model_dump()


def test_scorecard_triggers_direction_recompute(phase2_seed_data):
    service = IntelligenceService(phase2_seed_data)
    initial = service.compute_league("league_x")["directions"][1]
    phase2_seed_data.execute(
        "UPDATE rosters SET starters = '[\"qb1\",\"wr1\",\"te1\",\"rbb1\"]' WHERE league_id = 'league_x' AND roster_id = 1"
    )
    updated = service.compute_league("league_x")["directions"][1]
    assert initial.primary_label != "" and updated.primary_label != ""
