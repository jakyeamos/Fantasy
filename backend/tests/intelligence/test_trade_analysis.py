from datetime import datetime

from fantasy.trade.models import TradeAsset, TradeRequest
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.trade_engine import TradeEngine


def _request() -> TradeRequest:
    return TradeRequest(
        league_id="league_x",
        user_roster_id=1,
        counterparty_roster_id=2,
        user_sends=[
            TradeAsset(asset_type="player", player_id="wr1"),
            TradeAsset(
                asset_type="pick",
                pick_owner_roster_id=1,
                pick_year=2026,
                pick_round=2,
            ),
        ],
        user_receives=[TradeAsset(asset_type="player", player_id="qb2")],
        include_package=True,
    )


def _complete_analysis(conn, request: TradeRequest):
    engine = TradeEngine(conn)
    evaluation = engine.evaluate(request)
    evaluation.package = PackageBuilder(conn).build(request, evaluation)
    assert evaluation.package is not None
    return engine.build_analysis(request, evaluation)


def test_analysis_packet_contains_complete_layers(trade_seed_data):
    analysis = _complete_analysis(trade_seed_data, _request())

    assert analysis.schema_version == "trade-analysis/1.0"
    assert analysis.headline
    assert analysis.score_interpretation.startswith("This is a normalized decision score")
    assert {asset.side for asset in analysis.assets} == {
        "user_send",
        "user_receive",
        "counterparty_send",
        "counterparty_receive",
    }
    assert {scenario.scenario_type for scenario in analysis.scenarios} == {
        "current_offer",
        "aggressive_open",
        "preferred_close",
        "fallback",
        "walk_away",
    }
    assert analysis.negotiation.walk_away_rule
    assert analysis.lineup_impacts
    assert analysis.quality.completeness_score == 100.0
    assert analysis.quality.gates["scenario_analysis"] is True
    assert analysis.quality.gates["calibration_truth"] is False
    assert analysis.quality.calibration["status"] == "unavailable"
    assert analysis.quality.status == "complete_with_degraded_evidence"


def test_analysis_blocks_underspecified_pick_identity(trade_seed_data):
    request = _request()
    request.user_sends = [TradeAsset(asset_type="pick", pick_year=2026, pick_round=2)]
    analysis = _complete_analysis(trade_seed_data, request)

    assert analysis.quality.gates["exact_offer"] is False
    assert analysis.quality.gates["pick_identity"] is False
    assert analysis.quality.status == "blocked"
    assert any("pick" in limitation.lower() for limitation in analysis.quality.limitations)
    assert "not an empirical win probability" in analysis.score_interpretation


def test_analysis_expands_uncertainty_for_stale_ingest(trade_seed_data):
    trade_seed_data.execute(
        "UPDATE leagues SET ingested_at = ? WHERE league_id = 'league_x'",
        [datetime(2020, 1, 1)],
    )

    analysis = _complete_analysis(trade_seed_data, _request())

    assert analysis.quality.freshness["status"] == "stale"
    assert analysis.quality.status == "complete_with_degraded_evidence"
    assert analysis.quality.evidence_reliability_score < 100.0
    assert analysis.model_score_low < analysis.model_score_point < analysis.model_score_high
    assert any("fresh" in limitation.lower() for limitation in analysis.quality.limitations)
