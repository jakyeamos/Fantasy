from __future__ import annotations

from fantasy.actions.models import CommandAction, TradeSuggestion
from fantasy.decisions.adapter import decision_card_from_action


def test_command_action_maps_to_canonical_decision_card() -> None:
    card = decision_card_from_action(CommandAction(
        id="trade:league:1",
        league_id="league",
        roster_id=1,
        category="trade",
        priority_rank=1,
        urgency="today",
        confidence="HIGH",
        headline="Roster 2 needs a WR",
        recommended_action="Prepare a disciplined offer.",
        acceptable_price="Up to a late first",
        timing="Before the market moves.",
        why_now="The need is visible in the current roster.",
        risk_if_wrong="You overpay for short-term need.",
        evidence=["Lineup gap", "Manager history"],
        cta_label="Prepare trade",
        cta_destination="/trades?leagueId=league",
        stale_domains=["market"],
        trade_suggestion=TradeSuggestion(
            league_id="league",
            target_player_name="Target",
            target_manager_roster_id=2,
            send_player_ids=["send"],
            receive_player_ids=["receive"],
            acceptance_confidence="HIGH",
            manager_pitch_angle="Needs WR depth",
        ),
    ))

    assert card.lane == "trade"
    assert card.scope.asset_ids == ["send", "receive"]
    assert card.scope.manager_id == "2"
    assert card.confidence.band == "high"
    assert card.freshness.state == "stale"
    assert card.cta.destination.startswith("/trades")
