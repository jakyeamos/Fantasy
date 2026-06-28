from __future__ import annotations

from fantasy.actions.models import CommandAction

URGENCY_WEIGHT = {"today": 0, "this_week": 1, "watch": 2, "low": 3}
CONFIDENCE_WEIGHT = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
CATEGORY_WEIGHT = {
    "waiver": 0,
    "lineup": 1,
    "trade": 2,
    "manager": 3,
    "rookie_pick": 4,
    "portfolio": 5,
    "market": 6,
}


def action_sort_key(action: CommandAction) -> tuple[int, int, int, int, int, str]:
    return (
        URGENCY_WEIGHT[action.urgency],
        CONFIDENCE_WEIGHT[action.confidence],
        _execution_weight(action),
        CATEGORY_WEIGHT[action.category],
        action.priority_rank,
        action.headline.lower(),
    )


def _execution_weight(action: CommandAction) -> int:
    if action.trade_suggestion is not None:
        return 0
    if _is_prefilled_trade_lab(action.cta_destination):
        return 0
    if action.category in {"waiver", "lineup", "rookie_pick", "portfolio"}:
        return 1
    if action.category == "manager" and action.cta_label == "Open Trade Lab":
        return 1
    if action.category == "trade":
        return 2
    return 3


def _is_prefilled_trade_lab(destination: str) -> bool:
    if not destination.startswith("/trades?"):
        return False
    return (
        "sendPlayerId=" in destination
        and "receivePlayerId=" in destination
        and "counterpartyRosterId=" in destination
    )
