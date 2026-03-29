from __future__ import annotations

from fantasy.prospects.comp_finder import CompFinder
from fantasy.prospects.models import ProspectFeatures


def _wr(player_id: str, draft_ovr: int, outcome_bucket: str | None, rec_ypg: float, forty: float) -> ProspectFeatures:
    return ProspectFeatures(
        player_id=player_id,
        player_name=player_id,
        position="WR",
        draft_year=2020,
        age_at_draft=21.5,
        draft_ovr=draft_ovr,
        forty=forty,
        weight=205,
        height=72,
        vertical=36,
        cone=6.9,
        college_rec_ypg=rec_ypg,
        college_mkt_share_proxy=0.28,
        outcome_bucket=outcome_bucket,
    )


def test_comp_finder_filters_by_position_and_tier_and_returns_roles():
    finder = CompFinder()
    prospect = _wr("prospect", 18, None, 88, 4.45)
    pool = [
        _wr("hit_a", 20, "hit", 86, 4.46),
        _wr("med_a", 24, "mediocre", 80, 4.5),
        _wr("bust_a", 30, "bust", 60, 4.6),
        _wr("hit_b", 28, "hit", 84, 4.44),
        _wr("med_b", 16, "mediocre", 82, 4.49),
        _wr("bust_b", 26, "bust", 55, 4.58),
        _wr("other_tier", 80, "hit", 90, 4.4),
    ]

    comps, low_confidence = finder.find_comps(prospect, pool)

    assert [comp.role for comp in comps] == ["ceiling", "median", "floor"]
    assert all("similar" in comp.match_reason for comp in comps)
    assert low_confidence is False


def test_comp_finder_marks_low_confidence_when_pool_is_too_thin():
    finder = CompFinder()
    prospect = _wr("prospect", 18, None, 88, 4.45)
    pool = [
        _wr("hit_a", 20, "hit", 86, 4.46),
        _wr("med_a", 24, "mediocre", 80, 4.5),
        _wr("bust_a", 30, "bust", 60, 4.6),
    ]

    _, low_confidence = finder.find_comps(prospect, pool)

    assert low_confidence is True
