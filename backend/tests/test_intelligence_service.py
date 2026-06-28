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


def test_compute_league_tolerates_missing_player_rows(phase2_seed_data):
    phase2_seed_data.execute("DELETE FROM players")

    result = IntelligenceService(phase2_seed_data).compute_league("league_x")

    assert result["values"][1]["qb1"].player_id == "qb1"


def test_compute_league_populates_player_trend_result(phase2_seed_data):
    service = IntelligenceService(phase2_seed_data)

    result = service.compute_league("league_x")

    trend = result["values"][1]["wr1"].trend_result
    assert trend is not None
    assert trend.player_id == "wr1"

    persisted = service.get_player_value("league_x", 1, "wr1")
    assert persisted.trend_result is not None
    assert persisted.trend_result.player_id == "wr1"


def test_compute_league_propagates_trend_result_to_recommendation_cards(phase2_seed_data):
    result = IntelligenceService(phase2_seed_data).compute_league("league_x")

    cards = result["lineup"][1].recommendation_cards

    assert cards
    assert cards[0].trend_result is not None
