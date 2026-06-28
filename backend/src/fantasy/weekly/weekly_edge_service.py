from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

import duckdb

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.weekly.models import (
    LineupGapDecision,
    MatchupGrade,
    StartSitDecision,
    WeeklyEdgeResponse,
    WeeklyPlayerSignal,
)
from fantasy.weekly.public_context import ensure_weekly_context_schema

WEEKLY_EDGE_DOMAINS = ["injuries", "usage", "schedule", "stats"]


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class WeeklyEdgeService:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._freshness = FreshnessService(ContextRepo(conn))
        self._lineup_repo = LineupRepo(conn)

    def build(self, league_id: str, roster_id: int) -> WeeklyEdgeResponse:
        ensure_weekly_context_schema(self._conn)
        starter_ids, bench_ids = self._roster_players(league_id, roster_id)
        player_ids = starter_ids + bench_ids
        player_signals = self._player_signals(starter_ids, bench_ids)
        stale_domains = [
            tag.domain
            for tag in self._freshness.get_tags(league_id, WEEKLY_EDGE_DOMAINS)
            if tag.is_stale
        ]
        return WeeklyEdgeResponse(
            league_id=league_id,
            roster_id=roster_id,
            computed_at=datetime.now(timezone.utc).isoformat(),
            player_signals=player_signals,
            start_sit=self._start_sit_decisions(player_signals, stale_domains),
            lineup_gaps=self._lineup_gaps(league_id, roster_id, stale_domains),
            stale_domains=stale_domains,
        )

    def _roster_players(self, league_id: str, roster_id: int) -> tuple[list[str], list[str]]:
        row = self._conn.execute(
            """
            SELECT starters, players, reserve, taxi
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return [], []
        starters = [str(player_id) for player_id in _loads(row[0], []) if player_id]
        all_players = [str(player_id) for player_id in _loads(row[1], []) if player_id]
        protected = set(starters)
        protected.update(str(player_id) for player_id in _loads(row[2], []) if player_id)
        protected.update(str(player_id) for player_id in _loads(row[3], []) if player_id)
        bench = [
            player_id
            for player_id in all_players
            if player_id not in protected and player_id not in {"0", ""}
        ]
        return starters, bench

    def _player_signals(
        self,
        starter_ids: list[str],
        bench_ids: list[str],
    ) -> list[WeeklyPlayerSignal]:
        player_ids = starter_ids + bench_ids
        if not player_ids:
            return []
        rows = self._conn.execute(
            """
            WITH recent AS (
                SELECT player_id,
                       AVG(COALESCE(fantasy_points, 0)) AS recent_points,
                       AVG(
                           COALESCE(targets, 0) + COALESCE(carries, 0)
                           + COALESCE(passing_yards, 0) / 25.0
                       ) AS recent_opportunities
                FROM (
                    SELECT player_id, fantasy_points, targets, carries, passing_yards,
                           ROW_NUMBER() OVER (
                               PARTITION BY player_id ORDER BY season DESC, week DESC
                           ) AS rn
                    FROM player_stats_weekly
                    WHERE player_id IN (SELECT UNNEST(?))
                )
                WHERE rn <= 4
                GROUP BY player_id
            )
            SELECT p.player_id, COALESCE(p.full_name, p.player_id), COALESCE(p.position, 'FLEX'),
                   p.team, p.metadata_blob, COALESCE(recent.recent_points, 0),
                   COALESCE(recent.recent_opportunities, 0)
            FROM players p
            LEFT JOIN recent ON recent.player_id = p.player_id
            WHERE p.player_id IN (SELECT UNNEST(?))
            """,
            [player_ids, player_ids],
        ).fetchall()
        starter_set = set(starter_ids)
        team_contexts = self._team_contexts(
            [str(row[3]) for row in rows if row[3] is not None]
        )
        matchup_contexts = self._position_environment_contexts(
            [
                {
                    "team": str(team_contexts[str(row[3])]["opponent"]),
                    "position": str(row[2]),
                }
                for row in rows
                if row[3] is not None
                and str(row[3]) in team_contexts
                and team_contexts[str(row[3])].get("opponent") is not None
            ]
        )
        signals: list[WeeklyPlayerSignal] = []
        for row in rows:
            metadata = _loads(row[4], {})
            injury_status = str(
                metadata.get("injury_status")
                or metadata.get("status")
                or ""
            ).strip()
            warning = self._availability_warning(injury_status)
            availability = self._availability_status(injury_status)
            team = str(row[3]) if row[3] is not None else None
            context = team_contexts.get(team or "")
            matchup_context = matchup_contexts.get(
                (context or {}).get("opponent") or "",
                {},
            ).get(str(row[2]))
            matchup_grade = self._matchup_grade(context, matchup_context)
            matchup_note = self._matchup_note(context, matchup_grade)
            allowance_note = self._opponent_allowance_note(matchup_context)
            recent_points = float(row[5] or 0.0)
            recent_opportunities = float(row[6] or 0.0)
            usage_note = self._usage_note(recent_points, recent_opportunities)
            projection = self._projection_points(
                recent_points,
                recent_opportunities,
                matchup_grade,
                availability,
                context,
            )
            signals.append(
                WeeklyPlayerSignal(
                    player_id=str(row[0]),
                    player_name=str(row[1]),
                    position=str(row[2]),
                    team=team,
                    roster_slot="starter" if str(row[0]) in starter_set else "bench",
                    recent_points=round(recent_points, 2),
                    recent_opportunities=round(recent_opportunities, 2),
                    projection_points=projection,
                    opponent_team=context["opponent"] if context else None,
                    game_week=int(context["week"]) if context else None,
                    matchup_grade=matchup_grade,
                    matchup_note=matchup_note,
                    opponent_allowance_note=allowance_note,
                    usage_note=usage_note,
                    injury_status=injury_status or None,
                    availability_status=availability,
                    availability_warning=warning,
                )
            )
        signals.sort(
            key=lambda signal: (
                signal.roster_slot != "starter",
                signal.position,
                -signal.recent_points,
                signal.player_name.lower(),
            )
        )
        return signals

    def _team_contexts(self, teams: list[str]) -> dict[str, dict[str, Any]]:
        unique_teams = sorted({team for team in teams if team})
        if not unique_teams:
            return {}
        rows = self._conn.execute(
            """
            WITH ranked AS (
                SELECT team, season, week, opponent, is_home, game_date, game_type,
                       ROW_NUMBER() OVER (
                           PARTITION BY team
                           ORDER BY
                               CASE
                                   WHEN TRY_CAST(game_date AS DATE) >= CURRENT_DATE THEN 0
                                   ELSE 1
                               END,
                               CASE
                                   WHEN TRY_CAST(game_date AS DATE) >= CURRENT_DATE
                                   THEN TRY_CAST(game_date AS DATE)
                                   ELSE NULL
                               END ASC NULLS LAST,
                               season DESC,
                               week DESC
                       ) AS rn
                FROM team_schedule_weekly
                WHERE team IN (SELECT UNNEST(?))
            )
            SELECT team, season, week, opponent, is_home, game_date, game_type
            FROM ranked
            WHERE rn = 1
            """,
            [unique_teams],
        ).fetchall()
        return {
            str(row[0]): {
                "season": int(row[1]),
                "week": int(row[2]),
                "opponent": str(row[3]) if row[3] is not None else None,
                "is_home": bool(row[4]),
                "game_date": str(row[5]) if row[5] is not None else None,
                "game_type": str(row[6]) if row[6] is not None else None,
            }
            for row in rows
        }

    def _position_environment_contexts(
        self,
        team_positions: list[dict[str, str]],
    ) -> dict[str, dict[str, dict[str, float | int]]]:
        teams = sorted({row["team"] for row in team_positions if row.get("team")})
        positions = sorted({row["position"] for row in team_positions if row.get("position")})
        if not teams or not positions:
            return {}
        opponent_rows = self._conn.execute(
            """
            WITH recent AS (
                SELECT p.team, COALESCE(p.position, 'FLEX') AS position,
                       AVG(COALESCE(s.fantasy_points, 0)) AS position_points
                FROM player_stats_weekly s
                JOIN players p ON p.player_id = s.player_id
                WHERE p.team IS NOT NULL
                  AND COALESCE(p.position, 'FLEX') IN (SELECT UNNEST(?))
                  AND s.week >= (
                      SELECT COALESCE(MAX(week), 1) - 3
                      FROM player_stats_weekly
                  )
                GROUP BY p.team, COALESCE(p.position, 'FLEX')
            ),
            ranked AS (
                SELECT team, position, position_points,
                       RANK() OVER (PARTITION BY position ORDER BY position_points DESC) AS rank,
                       COUNT(*) OVER (PARTITION BY position) AS team_count
                FROM recent
            )
            SELECT team, position, position_points, rank, team_count
            FROM ranked
            WHERE team IN (SELECT UNNEST(?))
            """,
            [positions, teams],
        ).fetchall()
        contexts: dict[str, dict[str, dict[str, float | int]]] = {}
        for row in opponent_rows:
            team = str(row[0])
            position = str(row[1])
            contexts.setdefault(team, {})[position] = {
                "points": round(float(row[2] or 0.0), 2),
                "rank": int(row[3]),
                "team_count": int(row[4]),
            }
        return contexts

    def _matchup_note(
        self,
        context: dict[str, Any] | None,
        matchup_grade: MatchupGrade,
    ) -> str | None:
        if context is None or context.get("opponent") is None:
            return None
        venue = "home" if context.get("is_home") else "away"
        game_date = context.get("game_date")
        date_note = f" on {game_date}" if game_date else ""
        grade = {
            "plus": "plus",
            "neutral": "neutral",
            "minus": "tough",
            "bye": "bye-week",
            "unknown": "ungraded",
        }[matchup_grade]
        return (
            f"Week {context['week']} {venue} matchup vs {context['opponent']}{date_note} "
            f"({grade} setup)."
        )

    def _opponent_allowance_note(
        self,
        matchup_context: dict[str, float | int] | None,
    ) -> str | None:
        if matchup_context is None:
            return (
                "No local opponent positional environment sample yet; refresh weekly stats "
                "before treating matchup as a strong edge."
            )
        return (
            "Opponent position environment proxy: "
            f"rank {matchup_context['rank']}/{matchup_context['team_count']} "
            f"at {matchup_context['points']:.1f} recent points per player."
        )

    def _usage_note(self, recent_points: float, recent_opportunities: float) -> str:
        if recent_opportunities >= 12:
            return f"Strong recent usage: {recent_opportunities:.1f} weighted opportunities with {recent_points:.1f} PPG."
        if recent_opportunities >= 7:
            return f"Usable recent role: {recent_opportunities:.1f} weighted opportunities with {recent_points:.1f} PPG."
        return f"Thin recent role: {recent_opportunities:.1f} weighted opportunities with {recent_points:.1f} PPG."

    def _availability_warning(self, injury_status: str) -> str | None:
        normalized = injury_status.lower()
        if normalized in {"out", "doubtful", "ir", "injured reserve"}:
            return "Do not lock this player into a weekly lineup without an availability update."
        if normalized in {"questionable", "limited"}:
            return "Monitor active status before lineups lock."
        return None

    def _availability_status(
        self,
        injury_status: str,
    ) -> Literal["active", "monitor", "out", "unknown"]:
        normalized = injury_status.lower()
        if normalized in {"active", "healthy"}:
            return "active"
        if normalized in {"questionable", "limited"}:
            return "monitor"
        if normalized in {"out", "doubtful", "ir", "injured reserve"}:
            return "out"
        return "unknown"

    def _matchup_grade(
        self,
        context: dict[str, Any] | None,
        matchup_context: dict[str, float | int] | None,
    ) -> MatchupGrade:
        if context is None:
            return "unknown"
        if context.get("opponent") is None:
            return "bye"
        if matchup_context is None:
            return "unknown"
        rank = int(matchup_context["rank"])
        team_count = max(int(matchup_context["team_count"]), 1)
        if rank <= max(1, round(team_count * 0.30)):
            return "plus"
        if rank >= max(1, round(team_count * 0.70)):
            return "minus"
        return "neutral"

    def _projection_points(
        self,
        recent_points: float,
        recent_opportunities: float,
        matchup_grade: MatchupGrade,
        availability: Literal["active", "monitor", "out", "unknown"],
        context: dict[str, Any] | None,
    ) -> float:
        matchup_adjustment = {
            "plus": 1.5,
            "neutral": 0.0,
            "minus": -1.0,
            "bye": -8.0,
            "unknown": 0.0,
        }[matchup_grade]
        availability_penalty = {
            "active": 0.0,
            "monitor": 2.5,
            "out": 12.0,
            "unknown": 0.5,
        }[availability]
        home_adjustment = 0.3 if context and context.get("is_home") else 0.0
        projection = (
            recent_points
            + recent_opportunities * 0.18
            + matchup_adjustment
            + home_adjustment
            - availability_penalty
        )
        return round(max(0.0, projection), 2)

    def _start_sit_decisions(
        self,
        signals: list[WeeklyPlayerSignal],
        stale_domains: list[str],
    ) -> list[StartSitDecision]:
        starters = [signal for signal in signals if signal.roster_slot == "starter"]
        bench = [signal for signal in signals if signal.roster_slot == "bench"]
        decisions: list[StartSitDecision] = []
        for starter in starters:
            candidates = [
                signal
                for signal in bench
                if signal.position == starter.position
                or starter.position in {"FLEX", "WR", "RB", "TE"}
                and signal.position in {"WR", "RB", "TE"}
            ]
            if not candidates:
                continue
            best_bench = max(
                candidates,
                key=lambda signal: (
                    signal.projection_points,
                    signal.recent_points,
                ),
            )
            starter_score = starter.projection_points
            bench_score = best_bench.projection_points
            edge = round(bench_score - starter_score, 2)
            if edge < 2.0 and not starter.availability_warning:
                continue
            confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH" if edge >= 5 else "MEDIUM"
            if stale_domains:
                confidence = "MEDIUM" if confidence == "HIGH" else "LOW"
            if starter.availability_warning:
                confidence = "HIGH" if edge >= 1.0 and not stale_domains else "MEDIUM"
            decisions.append(
                StartSitDecision(
                    start_player_id=best_bench.player_id,
                    start_player_name=best_bench.player_name,
                    sit_player_id=starter.player_id,
                    sit_player_name=starter.player_name,
                    position=starter.position,
                    edge_points=max(edge, 0.0),
                    start_projection=best_bench.projection_points,
                    sit_projection=starter.projection_points,
                    confidence=confidence,
                    recommendation=f"Start {best_bench.player_name} over {starter.player_name}.",
                    why_now=(
                        f"{best_bench.player_name} projects {best_bench.projection_points:.1f} "
                        f"vs {starter.player_name} at {starter.projection_points:.1f}, using recent "
                        "points, role, availability, and matchup context."
                        + (
                            f" {best_bench.matchup_note}"
                            if best_bench.matchup_note
                            else ""
                        )
                        + (
                            f" {best_bench.opponent_allowance_note}"
                            if best_bench.opponent_allowance_note
                            else ""
                        )
                    ),
                    risk_if_wrong=(
                        starter.availability_warning
                        or "Recent usage can be noisy if roles changed after the latest public stats sample."
                    ),
                    stale_domains=stale_domains,
                )
            )
        decisions.sort(key=lambda item: (-item.edge_points, item.start_player_name.lower()))
        return decisions[:5]

    def _lineup_gaps(
        self,
        league_id: str,
        roster_id: int,
        stale_domains: list[str],
    ) -> list[LineupGapDecision]:
        cached = self._lineup_repo.get_lineup_result(league_id, roster_id)
        if cached is None:
            return []
        weak_slots = [
            slot
            for slot in cached.slot_scores
            if slot.below_playoff_target or slot.below_title_target
        ]
        weak_slots.sort(
            key=lambda slot: (
                -slot.gap_to_title_target,
                -slot.upgrade_leverage_score,
                slot.position,
            )
        )
        decisions: list[LineupGapDecision] = []
        for slot in weak_slots[:3]:
            confidence: Literal["HIGH", "MEDIUM", "LOW"] = (
                "HIGH" if slot.gap_to_title_target >= 10 else "MEDIUM"
            )
            if stale_domains and confidence == "HIGH":
                confidence = "MEDIUM"
            urgency: Literal["today", "this_week", "watch", "low"] = (
                "this_week" if slot.below_title_target else "watch"
            )
            decisions.append(
                LineupGapDecision(
                    position=slot.position,
                    current_player_id=slot.player_id,
                    current_player_name=slot.player_name,
                    gap_to_title_target=round(slot.gap_to_title_target, 2),
                    gap_to_playoff_target=round(slot.gap_to_playoff_target, 2),
                    recommended_action=(
                        f"Shop for a stronger {slot.position} starter or stream a higher-usage option."
                    ),
                    urgency=urgency,
                    confidence=confidence,
                    why_now=(
                        f"{slot.player_name} is {slot.gap_to_title_target:.1f} behind the title target "
                        f"and {slot.gap_to_playoff_target:.1f} behind the playoff target."
                    ),
                    stale_domains=stale_domains,
                )
            )
        return decisions
