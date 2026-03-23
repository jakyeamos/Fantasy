from __future__ import annotations

from fantasy.rookie.constants import GAP_THRESHOLD, MAX_TIER_COUNT
from fantasy.rookie.models import RookiePlayer
from fantasy.rookie.rookie_engine import RookieEngine, slot_availability_probability


class _FakeRepo:
    def __init__(self, league_settings: dict, players: list[dict]):
        self._league_settings = league_settings
        self._players = players
        self.saved_board = None
        self.saved_tendencies = None

    def get_league_settings(self, league_id: str) -> dict:
        assert league_id == "league_rookie"
        return self._league_settings

    def get_available_rookies(self, league_id: str) -> list[dict]:
        assert league_id == "league_rookie"
        return self._players

    def save_board_cache(self, league_id: str, class_strength_signal: float, board_json: str) -> None:
        self.saved_board = (league_id, class_strength_signal, board_json)

    def replace_league_tendencies(self, league_id: str, tendencies: list[dict]) -> None:
        self.saved_tendencies = (league_id, tendencies)

    def get_league_tendencies(self, league_id: str) -> list[dict]:
        return []


def _players() -> list[dict]:
    return [
        {"player_id": "wr1", "full_name": "WR One", "position": "WR", "age": 21, "adp": 1, "metadata": {"forty": 4.4, "target_share": 0.3, "draft_pick": 5}, "avg_fantasy_points": 0.0},
        {"player_id": "wr2", "full_name": "WR Two", "position": "WR", "age": 22, "adp": 3, "metadata": {"slot_rate": 0.6, "draft_pick": 20}, "avg_fantasy_points": 0.0},
        {"player_id": "rb1", "full_name": "RB One", "position": "RB", "age": 22, "adp": 5, "metadata": {"weight": 221, "draft_pick": 18}, "avg_fantasy_points": 0.0},
        {"player_id": "qb1", "full_name": "QB One", "position": "QB", "age": 22, "adp": 6, "metadata": {"mobile": True, "rush_yards": 500, "draft_pick": 8}, "avg_fantasy_points": 0.0},
        {"player_id": "te1", "full_name": "TE One", "position": "TE", "age": 22, "adp": 7, "metadata": {"move_te": True, "draft_pick": 12}, "avg_fantasy_points": 0.0},
        {"player_id": "wr3", "full_name": "WR Three", "position": "WR", "age": 24, "adp": 25, "metadata": {"injury_flag": True, "draft_pick": 140}, "avg_fantasy_points": 0.0},
    ]


def _engine(db, *, superflex: bool = False, ppr: float = 0.0, tep: bool = False) -> RookieEngine:
    engine = RookieEngine(db)
    engine._repo = _FakeRepo(
        {"league_size": 12, "superflex": superflex, "ppr": ppr, "tep": tep, "season": 2026},
        _players(),
    )
    return engine


def test_compute_board_returns_tiers_and_class_strength(db):
    engine = _engine(db, ppr=1.0)
    board = engine.compute_board("league_rookie")
    assert board.league_format == "PPR"
    assert board.tiers
    assert -1.0 <= board.class_strength_signal <= 1.0


def test_assign_tiers_creates_dynamic_breaks(db):
    engine = _engine(db)
    players = [
        RookiePlayer(player_id=str(index), full_name=str(index), position="WR", archetype_label="X", risk_band="Low", composite_score=score, tier_number=1, available_probability_by_slot={})
        for index, score in enumerate([90, 88, 87, 75, 73, 60], start=1)
    ]
    tiers = engine._assign_tiers(players)
    assert len(tiers) == 3
    assert GAP_THRESHOLD == 8.0


def test_assign_tiers_without_gaps_stays_single_tier(db):
    engine = _engine(db)
    players = [
        RookiePlayer(player_id=str(index), full_name=str(index), position="WR", archetype_label="X", risk_band="Low", composite_score=score, tier_number=1, available_probability_by_slot={})
        for index, score in enumerate([90, 86, 83, 80], start=1)
    ]
    assert len(engine._assign_tiers(players)) == 1


def test_assign_tiers_respects_max_tier_cap(db):
    engine = _engine(db)
    players = [
        RookiePlayer(player_id=str(index), full_name=str(index), position="WR", archetype_label="X", risk_band="Low", composite_score=score, tier_number=1, available_probability_by_slot={})
        for index, score in enumerate([100, 90, 80, 70, 60, 50, 40], start=1)
    ]
    assert len(engine._assign_tiers(players)) == MAX_TIER_COUNT


def test_score_rookie_superflex_boosts_qb(db):
    engine = _engine(db, superflex=True)
    qb = _players()[3]
    non_sf = _engine(db, superflex=False)
    assert engine._score_rookie(qb, {"superflex": True, "ppr": 0.0, "tep": False}) > non_sf._score_rookie(qb, {"superflex": False, "ppr": 0.0, "tep": False})


def test_score_rookie_full_ppr_boosts_pass_catchers(db):
    engine = _engine(db, ppr=1.0)
    wr = _players()[0]
    standard = _engine(db, ppr=0.0)
    assert engine._score_rookie(wr, {"superflex": False, "ppr": 1.0, "tep": False}) > standard._score_rookie(wr, {"superflex": False, "ppr": 0.0, "tep": False})


def test_score_rookie_tep_boosts_te(db):
    te = _players()[4]
    engine = _engine(db, tep=True)
    baseline = _engine(db, tep=False)
    assert engine._score_rookie(te, {"superflex": False, "ppr": 0.0, "tep": True}) > baseline._score_rookie(te, {"superflex": False, "ppr": 0.0, "tep": False})


def test_assign_archetype_uses_controlled_vocabulary(db):
    engine = _engine(db)
    assert engine._assign_archetype(_players()[0]) in {"Deep Threat", "Route Runner"}


def test_assign_archetype_falls_back_when_data_missing(db):
    engine = _engine(db)
    assert engine._assign_archetype({"position": "WR", "metadata": {}, "avg_fantasy_points": 0.0}) == "WR Prospect"


def test_assign_risk_band_returns_low_moderate_or_high(db):
    engine = _engine(db)
    assert engine._assign_risk_band(_players()[0]) == "Low"
    assert engine._assign_risk_band(_players()[2]) in {"Low", "Moderate"}
    assert engine._assign_risk_band(_players()[5]) == "High"


def test_compute_class_strength_positive_for_deep_top_tier(db):
    engine = _engine(db)
    players = [
        RookiePlayer(player_id=str(index), full_name=str(index), position="WR", archetype_label="X", risk_band="Low", composite_score=90 - index, tier_number=1 if index <= 5 else 2, available_probability_by_slot={})
        for index in range(1, 8)
    ]
    assert engine._compute_class_strength(players) > 0.0


def test_compute_class_strength_negative_for_thin_top_tier(db):
    engine = _engine(db)
    players = [
        RookiePlayer(player_id="1", full_name="1", position="WR", archetype_label="X", risk_band="Low", composite_score=90, tier_number=1, available_probability_by_slot={}),
        RookiePlayer(player_id="2", full_name="2", position="WR", archetype_label="X", risk_band="Low", composite_score=60, tier_number=3, available_probability_by_slot={}),
    ]
    assert engine._compute_class_strength(players) < 0.0


def test_compute_class_strength_baseline_is_neutral(db):
    engine = _engine(db)
    players = [
        RookiePlayer(player_id=str(index), full_name=str(index), position="WR", archetype_label="X", risk_band="Low", composite_score=90 - index, tier_number=1 if index <= 3 else 2, available_probability_by_slot={})
        for index in range(1, 9)
    ]
    assert engine._compute_class_strength(players) == 0.0


def test_compute_class_strength_empty_is_zero(db):
    engine = _engine(db)
    assert engine._compute_class_strength([]) == 0.0


def test_slot_availability_probability_curve():
    assert slot_availability_probability(rank=3, slot=1) == 0.05
    assert slot_availability_probability(rank=3, slot=3) == 0.50
    assert 0.50 < slot_availability_probability(rank=3, slot=10) <= 0.95


def test_format_label_variants(db):
    assert _engine(db, superflex=True, ppr=1.0)._format_label({"superflex": True, "ppr": 1.0, "tep": False}) == "Superflex · PPR"
    assert _engine(db, ppr=0.5)._format_label({"superflex": False, "ppr": 0.5, "tep": False}) == "Half PPR"
    assert _engine(db, tep=True)._format_label({"superflex": False, "ppr": 0.0, "tep": True}) == "TEP · Standard"
