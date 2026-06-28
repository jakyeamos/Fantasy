from __future__ import annotations

from fantasy.actions.command_center import CommandCenterEngine
from fantasy.actions.models import CommandAction


def _action(
    action_id: str,
    category: str,
    urgency: str,
    confidence: str,
    rank: int,
) -> CommandAction:
    return CommandAction(
        id=action_id,
        league_id="cmd5",
        roster_id=1,
        category=category,
        priority_rank=rank,
        urgency=urgency,
        confidence=confidence,
        headline=f"{category.title()} move {rank}",
        recommended_action="Send the offer at a fair price before waivers process.",
        why_now="The market window is open today.",
        risk_if_wrong="The role signal can reverse after injury news.",
        evidence=["Price: fair", "Risk: monitored", "CTA: ready"],
        cta_label="Open Decision",
        cta_destination=f"/decision/{rank}",
    )


def test_command_center_top_five_moves_are_actionable(db, monkeypatch):
    engine = CommandCenterEngine(db)
    rosters = [{"league_id": "cmd5", "roster_id": 1}]

    monkeypatch.setattr(engine, "_user_rosters", lambda league_id: rosters)
    monkeypatch.setattr(
        engine,
        "_waiver_actions",
        lambda _: [_action("waiver", "waiver", "today", "HIGH", 3)],
    )
    monkeypatch.setattr(
        engine,
        "_weekly_actions",
        lambda _: [_action("lineup", "lineup", "today", "MEDIUM", 1)],
    )
    monkeypatch.setattr(
        engine,
        "_opportunity_actions",
        lambda league_id: [_action("trade", "trade", "this_week", "HIGH", 2)],
    )
    monkeypatch.setattr(
        engine,
        "_manager_actions",
        lambda _: [_action("manager", "manager", "this_week", "MEDIUM", 4)],
    )
    monkeypatch.setattr(
        engine,
        "_portfolio_actions",
        lambda: [
            _action("portfolio", "portfolio", "watch", "MEDIUM", 5),
            _action("market", "market", "low", "LOW", 6),
        ],
    )

    response = engine.build()

    top_five = response.actions[:5]
    assert len(top_five) == 5
    assert [action.priority_rank for action in top_five] == [1, 2, 3, 4, 5]
    assert top_five[0].urgency == "today"
    for action in top_five:
        assert action.recommended_action
        assert action.why_now
        assert action.risk_if_wrong
        assert action.evidence
        assert action.cta_label
        assert action.cta_destination
    assert {tag.domain for tag in response.data_health} == {
        "injuries",
        "usage",
        "schedule",
        "waivers",
        "market",
        "stats",
    }
