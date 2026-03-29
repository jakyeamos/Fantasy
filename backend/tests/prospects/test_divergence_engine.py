from __future__ import annotations

from fantasy.prospects.divergence_engine import DivergenceEngine
from fantasy.prospects.models import ProspectFeatures


def test_divergence_engine_computes_direction_and_magnitude():
    engine = DivergenceEngine()

    direction, magnitude = engine.compute_divergence(
        player_id="p1",
        model_rankings=["p1", "p2", "p3"],
        adp_rankings=["p2", "p3", "p1"],
        low_confidence=False,
    )

    assert direction == "undervalued"
    assert magnitude == 2


def test_divergence_engine_builds_sub_flags_from_comp_medians():
    engine = DivergenceEngine()
    prospect = ProspectFeatures(
        player_id="p1",
        player_name="Prospect",
        position="WR",
        draft_year=2026,
        age_at_draft=21.0,
        draft_ovr=12,
        forty=4.42,
        weight=205,
        college_rec_ypg=92.0,
        college_mkt_share_proxy=0.32,
    )
    comps = [
        ProspectFeatures(
            player_id="c1",
            player_name="Comp 1",
            position="WR",
            draft_year=2020,
            age_at_draft=22.0,
            draft_ovr=18,
            forty=4.5,
            weight=198,
            college_rec_ypg=75.0,
            college_mkt_share_proxy=0.24,
        ),
        ProspectFeatures(
            player_id="c2",
            player_name="Comp 2",
            position="WR",
            draft_year=2021,
            age_at_draft=22.5,
            draft_ovr=22,
            forty=4.55,
            weight=200,
            college_rec_ypg=78.0,
            college_mkt_share_proxy=0.25,
        ),
    ]

    flags = engine.compute_sub_flags(prospect, comps)

    assert flags
    assert any(flag.signal_name == "Draft Capital" for flag in flags)
