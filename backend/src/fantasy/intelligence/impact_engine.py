from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import duckdb

from fantasy.intelligence.fresh_models import (
    EventType,
    FootballEvent,
    ImpactSummary,
    LeagueImpact,
    VerificationState,
)
from fantasy.portfolio.portfolio_repo import PortfolioRepo

MODEL_VERSION = "fresh-impact-v1"


def _loads(raw: str | None, fallback: Any) -> Any:
    try:
        return json.loads(raw) if raw else fallback
    except json.JSONDecodeError:
        return fallback


def _injury_delta(event: FootballEvent) -> float:
    status = str(event.details.get("status") or "").casefold()
    if any(token in status for token in ("out", "reserve", "ir", "pup")):
        return -0.30
    if "doubtful" in status:
        return -0.18
    if "questionable" in status:
        return -0.08
    if "limited" in status or "did not participate" in status:
        return -0.05
    if any(token in status for token in ("full", "active", "healthy")):
        return 0.05
    return -0.03


class LeagueImpactEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def compute(self, event: FootballEvent) -> list[LeagueImpact]:
        if not event.player_id:
            self._replace_canonical_projections(event, [])
            return []
        leagues = [str(row[0]) for row in self._conn.execute(
            "SELECT league_id FROM leagues ORDER BY league_id"
        ).fetchall()]
        user_by_league = {
            str(row["league_id"]): int(row["roster_id"])
            for row in PortfolioRepo(self._conn)._portfolio_roster_rows()
        }
        impacts: list[LeagueImpact] = []
        for league_id in leagues:
            impacts.extend(self._league_impacts(event, league_id, user_by_league.get(league_id)))
        exposed_leagues = [
            league_id
            for league_id, roster_id in user_by_league.items()
            if self._roster_owns(league_id, roster_id, event.player_id)
        ]
        if len(exposed_leagues) >= 2:
            impacts.append(self._impact(
                event=event, league_id=exposed_leagues[0], roster_id=user_by_league[exposed_leagues[0]],
                impact_type="portfolio_exposure",
                headline=f"{event.player_name or event.player_id} affects {len(exposed_leagues)} of your leagues",
                explanation=(
                    f"The same event is concentrated across {', '.join(exposed_leagues)}. "
                    "Treat the combined downside as a portfolio decision, not isolated lineup news."
                ), assets=[event.player_id], before={"exposed_leagues": len(exposed_leagues)},
                after={"exposed_leagues": len(exposed_leagues)},
                deltas={"portfolio_value": self._event_value_delta(event) * len(exposed_leagues)},
                actionable=event.verification_state is VerificationState.CONFIRMED,
                recommended_action="Review correlated exposure and hedge only where league prices permit.",
                cta_label="Open portfolio", cta_destination="/portfolio",
            ))
        self._replace_canonical_projections(event, impacts)
        return impacts

    def _replace_canonical_projections(
        self, event: FootballEvent, impacts: list[LeagueImpact]
    ) -> None:
        self._conn.execute(
            "DELETE FROM canonical_player_projections WHERE event_id = ?",
            [event.event_id],
        )
        if event.verification_state is not VerificationState.CONFIRMED:
            return
        for impact in impacts:
            summary = impact.impact_summary
            if "player_value" not in summary.deltas or not summary.affected_asset_ids:
                continue
            player_id = (
                summary.affected_asset_ids[0]
                if impact.impact_type == "direct_owner"
                else summary.affected_asset_ids[-1]
            )
            value_before = summary.before.get("player_value")
            value_after = summary.after.get("player_value")
            if value_before is None or value_after is None:
                continue
            availability_after = None
            if player_id == event.player_id and event.event_type in {
                EventType.INJURY_STATUS,
                EventType.PRACTICE_PARTICIPATION,
            }:
                availability_after = str(event.details.get("status") or "changed")
            role_before = float(value_before)
            role_after = float(value_after)
            self._conn.execute(
                """
                INSERT INTO canonical_player_projections (
                    projection_id, event_id, league_id, player_id,
                    availability_before, availability_after, role_before, role_after,
                    value_before, value_after, delta_json, confidence, invalidation,
                    model_version, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_id, league_id, player_id, model_version)
                DO UPDATE SET availability_before = EXCLUDED.availability_before,
                    availability_after = EXCLUDED.availability_after,
                    role_before = EXCLUDED.role_before, role_after = EXCLUDED.role_after,
                    value_before = EXCLUDED.value_before, value_after = EXCLUDED.value_after,
                    delta_json = EXCLUDED.delta_json, confidence = EXCLUDED.confidence,
                    invalidation = EXCLUDED.invalidation, computed_at = EXCLUDED.computed_at
                """,
                [
                    str(uuid4()), event.event_id, impact.league_id, player_id,
                    "available" if availability_after else None, availability_after,
                    role_before, role_after, float(value_before), float(value_after),
                    json.dumps(summary.deltas, sort_keys=True), impact.confidence,
                    impact.invalidation, MODEL_VERSION,
                    datetime.now(timezone.utc).replace(tzinfo=None),
                ],
            )

    def _league_impacts(
        self, event: FootballEvent, league_id: str, user_roster_id: int | None
    ) -> list[LeagueImpact]:
        roster_rows = self._conn.execute(
            "SELECT roster_id, players, starters, reserve, taxi FROM rosters WHERE league_id = ?",
            [league_id],
        ).fetchall()
        owner_by_player: dict[str, int] = {}
        roster_players: dict[int, list[str]] = {}
        for roster_id, players, starters, reserve, taxi in roster_rows:
            merged = {
                str(player)
                for raw in (players, starters, reserve, taxi)
                for player in _loads(raw, [])
                if player not in (None, "", 0, "0")
            }
            roster_players[int(roster_id)] = sorted(merged)
            for player_id in merged:
                owner_by_player[player_id] = int(roster_id)
        affected_owner = owner_by_player.get(event.player_id)
        player_row = self._conn.execute(
            "SELECT full_name, position, team FROM players WHERE player_id = ?",
            [event.player_id],
        ).fetchone()
        if not player_row:
            return []
        player_name = str(player_row[0] or event.player_name or event.player_id)
        position = str(player_row[1] or "UNKNOWN")
        team = str(player_row[2] or event.team or "")
        confirmed = event.verification_state is VerificationState.CONFIRMED
        scenario = event.verification_state in {
            VerificationState.WATCH,
            VerificationState.CONFLICTED,
            VerificationState.MANUAL_REVIEW,
        }
        if not confirmed and not scenario:
            return []

        value_before = self._market_value(event.player_id, league_id)
        delta = self._event_value_delta(event)
        value_after = max(0.0, min(1.0, value_before + delta))
        impacts: list[LeagueImpact] = []
        if affected_owner is not None:
            owner_need = self._positional_need(roster_players.get(affected_owner, []), position)
            pick_before, pick_after = self._pick_trajectory(
                league_id, affected_owner, delta if confirmed else 0.0
            )
            is_user = user_roster_id == affected_owner
            action = (
                f"Review {position} starters and replacement options before the next lineup lock."
                if is_user and confirmed
                else None
            )
            impacts.append(self._impact(
                event=event, league_id=league_id, roster_id=affected_owner,
                impact_type="direct_owner",
                headline=f"{player_name} changes roster {affected_owner}'s {position} outlook",
                explanation=(
                    f"{player_name}'s modeled value moves from {value_before:.2f} to {value_after:.2f}; "
                    f"the roster's {position} need is {owner_need}. Its tied pick trajectory moves "
                    f"from {pick_before:.2f} to {pick_after:.2f}."
                ),
                assets=[event.player_id],
                before={"player_value": value_before, "pick_trajectory": pick_before, "positional_need": owner_need},
                after={"player_value": value_after, "pick_trajectory": pick_after, "positional_need": owner_need},
                deltas={"player_value": delta if confirmed else 0.0,
                    "pick_trajectory": pick_after - pick_before},
                actionable=is_user and confirmed, recommended_action=action,
                cta_label="Open league" if is_user and confirmed else None,
                cta_destination=f"/league/{league_id}" if is_user and confirmed else None,
            ))

            if confirmed and user_roster_id is not None and affected_owner != user_roster_id:
                user_position_players = self._position_players(
                    roster_players.get(user_roster_id, []), position, exclude=event.player_id
                )
                if user_position_players:
                    trade_id, trade_name = user_position_players[-1]
                    impacts.append(self._impact(
                        event=event, league_id=league_id, roster_id=user_roster_id,
                        impact_type="trade_posture",
                        headline=f"Roster {affected_owner}'s new {position} need opens a trade lane",
                        explanation=(
                            f"{player_name}'s owner now has {owner_need} {position} need. "
                            f"{trade_name} is a user-owned conversation starter; price discipline still applies."
                        ), assets=[event.player_id, trade_id],
                        before={"target_roster_need": "pre-event", "candidate": trade_name},
                        after={"target_roster_need": owner_need, "candidate": trade_name},
                        deltas={"trade_posture": abs(delta)}, actionable=True,
                        recommended_action=(
                            f"Prepare an offer around {trade_name}; do not send it until the return clears your league-specific threshold."
                        ), cta_label="Prepare trade",
                        cta_destination=(
                            f"/trades?leagueId={league_id}&userRosterId={user_roster_id}"
                            f"&targetRosterId={affected_owner}"
                        ),
                    ))

        replacements = self._replacement_candidates(team, position, event.player_id)
        for candidate_id, candidate_name, candidate_value in replacements[:3]:
            candidate_owner = owner_by_player.get(candidate_id)
            opportunity_delta = max(0.03, abs(delta) * 0.45) if event.event_type is EventType.INJURY_STATUS else max(0.02, abs(delta) * 0.25)
            candidate_after = min(1.0, candidate_value + opportunity_delta)
            actionable = confirmed and (
                candidate_owner == user_roster_id or candidate_owner is None
            )
            if candidate_owner is None:
                action = f"Check waivers for {candidate_name}; the role gain is already tied to this event."
                label = "Open waivers"
                destination = f"/league/{league_id}/waivers"
                impact_type = "waiver_opportunity"
            elif candidate_owner == user_roster_id:
                action = f"Reassess {candidate_name}'s lineup and trade value before the market adjusts."
                label = "Open roster moves"
                destination = f"/league/{league_id}/roster-moves"
                impact_type = "owned_replacement"
            else:
                action = None
                label = None
                destination = None
                impact_type = "downstream_teammate"
            impacts.append(self._impact(
                event=event, league_id=league_id, roster_id=candidate_owner,
                impact_type=impact_type,
                headline=f"{candidate_name} inherits opportunity from {player_name}",
                explanation=(
                    f"The shared {team} {position} role creates a modeled value change from "
                    f"{candidate_value:.2f} to {candidate_after:.2f}."
                ),
                assets=[event.player_id, candidate_id],
                before={"player_value": candidate_value, "owner_roster_id": candidate_owner},
                after={"player_value": candidate_after, "owner_roster_id": candidate_owner},
                deltas={"player_value": opportunity_delta if confirmed else 0.0},
                actionable=actionable, recommended_action=action,
                cta_label=label, cta_destination=destination,
            ))

        # A league with neither direct ownership nor a plausible replacement consequence is irrelevant.
        return impacts

    def _event_value_delta(self, event: FootballEvent) -> float:
        if event.verification_state is not VerificationState.CONFIRMED:
            return 0.0
        if event.event_type in {EventType.INJURY_STATUS, EventType.PRACTICE_PARTICIPATION}:
            return _injury_delta(event)
        if event.event_type is EventType.USAGE_SHIFT:
            return max(-0.25, min(0.25, float(event.details.get("delta") or 0.0) * 0.35))
        if event.event_type is EventType.DEPTH_CHART_ROLE:
            rank = int(event.details.get("depth_rank") or 3)
            return {1: 0.08, 2: 0.02}.get(rank, -0.03)
        if event.event_type is EventType.MARKET_VALUE_CHANGE:
            return max(-0.15, min(0.15, float(event.details.get("trend_30day") or 0.0) / 10_000))
        return 0.03

    def _market_value(self, player_id: str, league_id: str) -> float:
        row = self._conn.execute(
            """
            SELECT lens_market FROM player_values
            WHERE league_id = ? AND player_id = ? ORDER BY computed_at DESC LIMIT 1
            """,
            [league_id, player_id],
        ).fetchone()
        if row and row[0] is not None:
            return max(0.0, min(1.0, float(row[0])))
        adp = self._conn.execute(
            "SELECT adp FROM player_adp_baseline WHERE player_id = ? ORDER BY loaded_at DESC LIMIT 1",
            [player_id],
        ).fetchone()
        return max(0.0, min(1.0, 1 - float(adp[0]) / 250)) if adp and adp[0] else 0.5

    def _replacement_candidates(
        self, team: str, position: str, excluded_player_id: str
    ) -> list[tuple[str, str, float]]:
        if not team or position == "UNKNOWN":
            return []
        rows = self._conn.execute(
            """
            SELECT player_id, full_name FROM players
            WHERE team = ? AND position = ? AND player_id <> ?
            ORDER BY full_name LIMIT 12
            """,
            [team, position, excluded_player_id],
        ).fetchall()
        candidates = [
            (str(row[0]), str(row[1] or row[0]), self._market_value(str(row[0]), ""))
            for row in rows
        ]
        candidates.sort(key=lambda item: (-item[2], item[1]))
        return candidates

    def _positional_need(self, player_ids: list[str], position: str) -> str:
        if not player_ids:
            return "high"
        count = int(self._conn.execute(
            "SELECT COUNT(*) FROM players WHERE player_id IN (SELECT UNNEST(?)) AND position = ?",
            [player_ids, position],
        ).fetchone()[0])
        thresholds = {"QB": 3, "RB": 5, "WR": 6, "TE": 3}
        target = thresholds.get(position, 3)
        return "high" if count <= target - 2 else "medium" if count < target else "low"

    def _position_players(
        self, player_ids: list[str], position: str, *, exclude: str
    ) -> list[tuple[str, str]]:
        if not player_ids:
            return []
        rows = self._conn.execute(
            """
            SELECT player_id, full_name FROM players
            WHERE player_id IN (SELECT UNNEST(?)) AND position = ? AND player_id <> ?
            ORDER BY full_name
            """,
            [player_ids, position, exclude],
        ).fetchall()
        return [(str(row[0]), str(row[1] or row[0])) for row in rows]

    def _roster_owns(self, league_id: str, roster_id: int, player_id: str) -> bool:
        row = self._conn.execute(
            "SELECT players, starters, reserve, taxi FROM rosters WHERE league_id = ? AND roster_id = ?",
            [league_id, roster_id],
        ).fetchone()
        return bool(row and any(player_id in _loads(raw, []) for raw in row))

    def _pick_trajectory(self, league_id: str, roster_id: int, value_delta: float) -> tuple[float, float]:
        row = self._conn.execute(
            """
            SELECT AVG(expected_draft_slot) FROM pick_values
            WHERE league_id = ? AND pick_owner_roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        before = float(row[0]) if row and row[0] is not None else 6.5
        # Lower roster strength moves the owner's picks earlier (toward slot 1).
        after = max(1.0, min(16.0, before + value_delta * 4.0))
        return before, after

    def _impact(
        self, *, event: FootballEvent, league_id: str, roster_id: int | None,
        impact_type: str, headline: str, explanation: str, assets: list[str],
        before: dict[str, Any], after: dict[str, Any], deltas: dict[str, float],
        actionable: bool, recommended_action: str | None, cta_label: str | None,
        cta_destination: str | None,
    ) -> LeagueImpact:
        return LeagueImpact(
            impact_id=str(uuid4()), event_id=event.event_id, league_id=league_id,
            roster_id=roster_id, impact_type=impact_type, headline=headline,
            explanation=explanation,
            impact_summary=ImpactSummary(affected_asset_ids=assets, before=before, after=after, deltas=deltas),
            confidence=event.confidence, actionable=actionable,
            recommended_action=recommended_action, cta_label=cta_label,
            cta_destination=cta_destination,
            invalidation="A newer official status, role update, transaction, or material usage sample supersedes this event.",
            model_version=MODEL_VERSION, computed_at=datetime.now(timezone.utc),
        )


__all__ = ["LeagueImpactEngine", "MODEL_VERSION"]
