from __future__ import annotations

from urllib.parse import quote_plus

from fantasy.actions.models import CommandAction
from fantasy.weekly.models import WeeklyEdgeResponse, WeeklyPlayerSignal


def build_weekly_risk_action(
    *,
    league_name: str,
    edge: WeeklyEdgeResponse,
    covered_player_ids: set[str],
) -> CommandAction | None:
    signal = _top_uncovered_risk(edge, covered_player_ids)
    if signal is None:
        return None
    is_bye = signal.bye_week_warning is not None
    verb = "replace" if is_bye or signal.availability_status == "out" else "check"
    return CommandAction(
        id=f"weekly:risk:{edge.league_id}:{edge.roster_id}:{signal.player_id}",
        league_id=edge.league_id,
        roster_id=edge.roster_id,
        category="lineup",
        priority_rank=1,
        urgency="today",
        confidence=_confidence(signal, edge.stale_domains),
        headline=f"{league_name}: {verb} {signal.player_name}",
        recommended_action=_recommended_action(signal),
        acceptable_price=_acceptable_price(signal),
        timing="Before lineups lock.",
        why_now=_why_now(signal),
        risk_if_wrong=_risk_if_wrong(signal),
        evidence=_evidence(signal),
        cta_label="Open Weekly Edge",
        cta_destination=(
            f"/league/{edge.league_id}?rosterId={edge.roster_id}&focus=weekly"
            f"&playerId={quote_plus(signal.player_id)}"
        ),
        stale_domains=_stale_domains(signal, edge.stale_domains),
    )


def _top_uncovered_risk(
    edge: WeeklyEdgeResponse,
    covered_player_ids: set[str],
) -> WeeklyPlayerSignal | None:
    risks = [
        signal
        for signal in edge.player_signals
        if signal.roster_slot == "starter"
        and signal.player_id not in covered_player_ids
        and (signal.bye_week_warning or signal.availability_warning)
    ]
    if not risks:
        return None
    risks.sort(
        key=lambda signal: (
            _risk_weight(signal),
            signal.projection_points,
            signal.player_name.lower(),
        )
    )
    return risks[0]


def _risk_weight(signal: WeeklyPlayerSignal) -> int:
    if signal.bye_week_warning is not None:
        return 0
    if signal.availability_status == "out":
        return 1
    return 2


def _confidence(signal: WeeklyPlayerSignal, stale_domains: list[str]) -> str:
    relevant_stale = _stale_domains(signal, stale_domains)
    if relevant_stale:
        return "MEDIUM"
    if signal.availability_status == "monitor":
        return "MEDIUM"
    return "HIGH"


def _recommended_action(signal: WeeklyPlayerSignal) -> str:
    if signal.bye_week_warning is not None:
        return f"Find a lineup replacement for {signal.player_name} before lineups lock."
    if signal.availability_status == "out":
        return f"Replace {signal.player_name}; do not leave an unavailable starter locked in."
    return f"Check {signal.player_name}'s active status before lineups lock."


def _acceptable_price(signal: WeeklyPlayerSignal) -> str:
    if signal.bye_week_warning is not None:
        return "No trade premium; use a bench pivot, waiver patch, or short rental."
    if signal.availability_status == "out":
        return "No asset premium; replace the unavailable starter with your best active option."
    return "No asset cost yet; pay only if fresh status confirms the lineup risk."


def _why_now(signal: WeeklyPlayerSignal) -> str:
    if signal.bye_week_warning is not None:
        return (
            f"{signal.player_name} has no scheduled opponent in the local weekly "
            "schedule context."
        )
    if signal.availability_warning is not None:
        return signal.availability_warning
    return "Weekly lineup context flags this starter as a lock-risk decision."


def _risk_if_wrong(signal: WeeklyPlayerSignal) -> str:
    if signal.bye_week_warning is not None:
        return (
            "Wrong if local schedule data is stale or the team context refresh changes "
            "this game week."
        )
    return (
        "Wrong if fresh injury news clears the player before lock or the latest status "
        "has not been refreshed."
    )


def _evidence(signal: WeeklyPlayerSignal) -> list[str]:
    evidence = [f"Availability: {signal.availability_status}"]
    if signal.bye_week_warning is not None:
        evidence.append(f"Schedule: {signal.bye_week_warning}")
    elif signal.matchup_note is not None:
        evidence.append(f"Schedule: {signal.matchup_note}")
    if signal.usage_note is not None:
        evidence.append(f"Usage: {signal.usage_note}")
    if signal.role_note is not None:
        evidence.append(f"Role: {signal.role_note}")
    return evidence


def _stale_domains(
    signal: WeeklyPlayerSignal,
    stale_domains: list[str],
) -> list[str]:
    relevant: list[str] = []
    if signal.bye_week_warning is not None and "schedule" in stale_domains:
        relevant.append("schedule")
    if signal.availability_warning is not None and "injuries" in stale_domains:
        relevant.append("injuries")
    return relevant
