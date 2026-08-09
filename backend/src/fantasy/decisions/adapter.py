from __future__ import annotations

from fantasy.actions.models import CommandAction
from fantasy.decisions.models import (
    DecisionCard,
    DecisionCardsResponse,
    DecisionConfidenceModel,
    DecisionCta,
    DecisionFreshness,
    DecisionScope,
)


def _confidence(value: str) -> str:
    return value.casefold()


def decision_card_from_action(action: CommandAction) -> DecisionCard:
    asset_ids: list[str] = []
    manager_id = None
    if action.trade_suggestion:
        asset_ids = [
            *action.trade_suggestion.send_player_ids,
            *action.trade_suggestion.receive_player_ids,
        ]
        if action.trade_suggestion.target_manager_roster_id is not None:
            manager_id = str(action.trade_suggestion.target_manager_roster_id)
    stale = list(action.stale_domains)
    return DecisionCard(
        id=action.id,
        lane="draft" if action.category == "rookie_pick" else action.category,
        scope=DecisionScope(
            league_id=action.league_id,
            roster_id=action.roster_id,
            asset_ids=asset_ids,
            manager_id=manager_id,
        ),
        action=action.recommended_action,
        outcome=action.headline,
        timing=action.timing,
        urgency=action.urgency,
        confidence=DecisionConfidenceModel(
            band=_confidence(action.confidence),
            explanation=action.why_now,
        ),
        acceptable_price=action.acceptable_price,
        risk=action.risk_if_wrong,
        invalidation=(
            f"Refresh {', '.join(stale)} before acting."
            if stale
            else "Recheck the attached evidence before execution."
        ),
        evidence=action.evidence,
        freshness=DecisionFreshness(state="stale" if stale else "fresh", domains=stale),
        cta=DecisionCta(label=action.cta_label, destination=action.cta_destination),
    )


def decision_cards_from_actions(
    actions: list[CommandAction], computed_at: str
) -> DecisionCardsResponse:
    cards = [decision_card_from_action(action) for action in actions]
    return DecisionCardsResponse(cards=cards, total=len(cards), computed_at=computed_at)


__all__ = ["decision_card_from_action", "decision_cards_from_actions"]
