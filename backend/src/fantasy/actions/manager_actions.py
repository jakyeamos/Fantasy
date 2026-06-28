from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import duckdb

from fantasy.actions.models import CommandAction, TradeSuggestion
from fantasy.actions.trade_suggestions import TradeSuggestionBuilder
from fantasy.profiling.models import ManagerSummary, PitchAngle
from fantasy.profiling.profiling_repo import ProfilingRepo


def build_manager_actions(
    conn: duckdb.DuckDBPyConnection,
    rosters: list[dict[str, object]],
    league_name: Callable[[str], str],
) -> list[CommandAction]:
    actions: list[CommandAction] = []
    suggestions = TradeSuggestionBuilder(conn)
    repo = ProfilingRepo(conn)
    for roster in rosters:
        league_id = str(roster["league_id"])
        user_roster_id = int(roster["roster_id"])
        for summary in _strong_summaries(repo, league_id, user_roster_id):
            angle = summary.top_pitch_angle
            if angle is None:
                continue
            confidence = _confidence(summary)
            pitch = _pitch_text(angle)
            suggestion = suggestions.build_manager_suggestion(
                league_id=league_id,
                user_roster_id=user_roster_id,
                target_roster_id=summary.roster_id,
                confidence=confidence,
                manager_pitch_angle=pitch,
            )
            if suggestion is None:
                continue
            actions.append(
                _action(
                    summary=summary,
                    league_name=league_name(league_id),
                    user_roster_id=user_roster_id,
                    confidence=confidence,
                    pitch=pitch,
                    suggestion=suggestion,
                    destination=suggestions.destination_for_suggestion(
                        league_id,
                        user_roster_id,
                        suggestion,
                    ),
                )
            )
            break
    return actions


def _strong_summaries(
    repo: ProfilingRepo,
    league_id: str,
    user_roster_id: int,
) -> list[ManagerSummary]:
    return [
        summary
        for summary in repo.list_manager_summaries(league_id)
        if summary.roster_id != user_roster_id
        and not summary.low_confidence
        and summary.evidence_count >= 5
        and summary.top_pitch_angle is not None
    ]


def _action(
    *,
    summary: ManagerSummary,
    league_name: str,
    user_roster_id: int,
    confidence: Literal["HIGH", "MEDIUM", "LOW"],
    pitch: str,
    suggestion: TradeSuggestion,
    destination: str,
) -> CommandAction:
    send = ", ".join(suggestion.send_assets)
    receive = ", ".join(suggestion.receive_assets)
    return CommandAction(
        id=f"manager:{summary.league_id}:{summary.roster_id}",
        league_id=summary.league_id,
        roster_id=user_roster_id,
        category="manager",
        priority_rank=max(1, 100 - round(summary.exploitability_score)),
        urgency="this_week",
        confidence=confidence,
        headline=f"Pitch {summary.manager_name} in {league_name}",
        recommended_action=f"Offer {send} for {receive}; lead with {pitch}",
        why_now=(
            f"{summary.manager_name} has a strong enough trade sample to make this "
            "a pitchable manager-specific window."
        ),
        risk_if_wrong=(
            "Manager tendency samples can age quickly if recent trades changed their build "
            "or the selected player is not actually available."
        ),
        evidence=[
            f"Evidence count: {summary.evidence_count}",
            f"Exploitability: {round(summary.exploitability_score)}",
            f"Send: {send}",
            f"Receive: {receive}",
            f"Fairness: {suggestion.fairness_band}",
        ],
        cta_label="Open Trade Lab",
        cta_destination=destination,
        trade_suggestion=suggestion,
    )


def _confidence(summary: ManagerSummary) -> Literal["HIGH", "MEDIUM", "LOW"]:
    if summary.evidence_count >= 8 and summary.exploitability_score >= 70:
        return "HIGH"
    return "MEDIUM"


def _pitch_text(angle: PitchAngle) -> str:
    return (
        f"open with {angle.send_description}; avoid {angle.avoid_description}. "
        f"{angle.reasoning}"
    )
