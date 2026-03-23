from __future__ import annotations

from datetime import datetime, timezone

from fantasy.rookie.models import DraftRoomResult, RookieBoardResult, RookiePlayer, RookieTier
from fantasy.rookie.rookie_engine import RookieEngine


class _DraftRoomRepo:
    def __init__(self):
        self.settings = {"league_size": 12, "superflex": True, "ppr": 1.0, "tep": False, "season": 2026}
        self.tendencies = []

    def get_league_settings(self, league_id: str) -> dict:
        return self.settings

    def get_available_rookies(self, league_id: str) -> list[dict]:
        return []

    def save_board_cache(self, league_id: str, class_strength_signal: float, board_json: str) -> None:
        return None

    def replace_league_tendencies(self, league_id: str, tendencies: list[dict]) -> None:
        self.tendencies = tendencies

    def get_league_tendencies(self, league_id: str) -> list[dict]:
        return self.tendencies


def _player(player_id: str, tier_number: int, score: float) -> RookiePlayer:
    return RookiePlayer(
        player_id=player_id,
        full_name=player_id,
        position="WR",
        archetype_label="Route Runner",
        risk_band="Low",
        composite_score=score,
        tier_number=tier_number,
        available_probability_by_slot={"1.03": 0.6, "1.06": 0.5},
    )


def _board(class_strength: float, players: list[RookiePlayer]) -> RookieBoardResult:
    tiers = []
    for tier_number in sorted({player.tier_number for player in players}):
        tiers.append(
            RookieTier(
                tier_number=tier_number,
                label=f"Tier {tier_number}",
                players=[player for player in players if player.tier_number == tier_number],
            )
        )
    return RookieBoardResult(
        league_id="league_rookie",
        league_format="Superflex · PPR",
        class_strength_signal=class_strength,
        tiers=tiers,
        computed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_compute_draft_room_returns_result(db):
    engine = RookieEngine(db)
    repo = _DraftRoomRepo()
    engine._repo = repo
    engine.compute_board = lambda league_id: _board(0.1, [_player("elite", 1, 90.0)])  # type: ignore[method-assign]
    result = engine.compute_draft_room("league_rookie", 3)
    assert isinstance(result, DraftRoomResult)
    assert result.trade_verdict.label


def test_trade_verdict_uses_pick_for_tier_one(db):
    engine = RookieEngine(db)
    verdict = engine._compute_trade_verdict(3, _board(0.1, [_player("elite", 1, 90.0)]), _player("elite", 1, 90.0))
    assert verdict.verdict == "use"


def test_trade_verdict_uses_pick_for_strong_tier_two(db):
    engine = RookieEngine(db)
    player = _player("strong", 2, 70.0)
    verdict = engine._compute_trade_verdict(6, _board(0.1, [player]), player)
    assert verdict.verdict == "use"


def test_trade_verdict_trades_weak_early_class(db):
    engine = RookieEngine(db)
    player = _player("weak", 3, 55.0)
    verdict = engine._compute_trade_verdict(2, _board(-0.3, [player]), player)
    assert verdict.verdict == "trade"


def test_trade_verdict_trades_when_no_player_available(db):
    engine = RookieEngine(db)
    verdict = engine._compute_trade_verdict(6, _board(0.0, []), None)
    assert verdict.verdict == "trade"


def test_build_tendency_warnings_emits_positional_run_and_value_gap(db):
    engine = RookieEngine(db)
    warnings = engine._build_tendency_warnings(
        [
            {"tendency_type": "positional_run", "position": "WR", "early_draft_slots": 1.5},
            {"tendency_type": "value_gap", "player_name": "Elite WR", "adp_delta": 2.5, "system_value_slot": 4},
        ],
        [],
        3,
    )
    assert {warning.warning_type for warning in warnings} == {"positional_run", "value_gap"}


def test_build_tendency_warnings_returns_empty_when_no_thresholds(db):
    engine = RookieEngine(db)
    warnings = engine._build_tendency_warnings(
        [{"tendency_type": "value_gap", "player_name": "Elite WR", "adp_delta": 1.0, "system_value_slot": 4}],
        [],
        3,
    )
    assert warnings == []


def test_format_slot_uses_round_notation(db):
    engine = RookieEngine(db)
    assert engine._format_slot(6) == "1.06"
    assert engine._format_slot(13) == "2.01"
