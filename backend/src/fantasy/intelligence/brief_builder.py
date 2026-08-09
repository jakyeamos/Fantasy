from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from fantasy.intelligence.event_store import IntelligenceStore
from fantasy.intelligence.fresh_models import (
    BriefItem,
    FootballEvent,
    LeagueImpact,
    VerificationState,
)


def _delta_size(impact: LeagueImpact) -> float:
    return max((abs(float(value)) for value in impact.impact_summary.deltas.values()), default=0.0)


class MorningBriefBuilder:
    def __init__(self, store: IntelligenceStore) -> None:
        self._store = store

    def build(self) -> list[BriefItem]:
        events = self._store.list_events(states=[
            VerificationState.CONFIRMED,
            VerificationState.WATCH,
            VerificationState.CONFLICTED,
            VerificationState.MANUAL_REVIEW,
        ])
        event_by_id = {event.event_id: event for event in events}
        impacts = [impact for impact in self._store.list_impacts() if impact.event_id in event_by_id]
        items: list[BriefItem] = []

        # What changed only includes external facts with a real league consequence.
        primary_by_event: dict[str, LeagueImpact] = {}
        for impact in impacts:
            current = primary_by_event.get(impact.event_id)
            if current is None or self._rank(impact) > self._rank(current):
                primary_by_event[impact.event_id] = impact
        for event_id, impact in primary_by_event.items():
            event = event_by_id[event_id]
            if event.verification_state is VerificationState.CONFIRMED:
                items.append(self._item(event, impact, "changed", 0))

        # Prepared moves: at most five globally and three in one league.
        per_league: defaultdict[str, int] = defaultdict(int)
        ranked_actions = sorted(
            (impact for impact in impacts if impact.actionable),
            key=self._rank,
            reverse=True,
        )
        selected = 0
        for impact in ranked_actions:
            if selected >= 5 or per_league[impact.league_id] >= 3:
                continue
            event = event_by_id[impact.event_id]
            if event.verification_state is not VerificationState.CONFIRMED:
                continue
            selected += 1
            per_league[impact.league_id] += 1
            items.append(self._item(event, impact, "best_move", selected))

        # Watch stays separate and never masquerades as an action.
        watch_rank = 0
        for event in events:
            if event.verification_state not in {
                VerificationState.WATCH,
                VerificationState.CONFLICTED,
                VerificationState.MANUAL_REVIEW,
            }:
                continue
            related = [impact for impact in impacts if impact.event_id == event.event_id]
            if not related:
                continue
            watch_rank += 1
            items.append(self._item(event, max(related, key=self._rank), "watch", watch_rank))
        lane_order = {"best_move": 0, "changed": 1, "watch": 2}
        items.sort(key=lambda item: (lane_order[item.lane], item.priority_rank, item.item_id))
        return items

    @staticmethod
    def _rank(impact: LeagueImpact) -> tuple[int, float, float]:
        return (int(impact.actionable), _delta_size(impact), impact.confidence)

    @staticmethod
    def _item(
        event: FootballEvent, impact: LeagueImpact, lane: str, priority_rank: int
    ) -> BriefItem:
        return BriefItem(
            item_id=str(uuid4()), event_id=event.event_id,
            league_id=impact.league_id, roster_id=impact.roster_id,
            lane=lane, priority_rank=priority_rank,
            headline=impact.headline,
            why_it_matters=impact.explanation,
            recommended_action=impact.recommended_action if lane == "best_move" else None,
            confidence=impact.confidence,
            source_summary=(
                f"{event.verification_state.value}; {len(event.observation_ids)} supporting observation"
                f"{'s' if len(event.observation_ids) != 1 else ''}"
            ),
            invalidation=impact.invalidation,
            impact_summary=impact.impact_summary,
            cta_label=impact.cta_label if lane == "best_move" else None,
            cta_destination=impact.cta_destination if lane == "best_move" else None,
        )


__all__ = ["MorningBriefBuilder"]
