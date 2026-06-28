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
    StartSitDecision,
    WeeklyEdgeResponse,
    WeeklyPlayerSignal,
)

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
        signals: list[WeeklyPlayerSignal] = []
        for row in rows:
            metadata = _loads(row[4], {})
            injury_status = str(
                metadata.get("injury_status")
                or metadata.get("status")
                or ""
            ).strip()
            warning = self._availability_warning(injury_status)
            signals.append(
                WeeklyPlayerSignal(
                    player_id=str(row[0]),
                    player_name=str(row[1]),
                    position=str(row[2]),
                    team=str(row[3]) if row[3] is not None else None,
                    roster_slot="starter" if str(row[0]) in starter_set else "bench",
                    recent_points=round(float(row[5] or 0.0), 2),
                    recent_opportunities=round(float(row[6] or 0.0), 2),
                    injury_status=injury_status or None,
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

    def _availability_warning(self, injury_status: str) -> str | None:
        normalized = injury_status.lower()
        if normalized in {"out", "doubtful", "ir", "injured reserve"}:
            return "Do not lock this player into a weekly lineup without an availability update."
        if normalized in {"questionable", "limited"}:
            return "Monitor active status before lineups lock."
        return None

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
                    signal.recent_points + signal.recent_opportunities * 0.18,
                    signal.recent_points,
                ),
            )
            starter_score = starter.recent_points + starter.recent_opportunities * 0.18
            bench_score = best_bench.recent_points + best_bench.recent_opportunities * 0.18
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
                    confidence=confidence,
                    recommendation=f"Start {best_bench.player_name} over {starter.player_name}.",
                    why_now=(
                        f"{best_bench.player_name} has the stronger recent points/opportunity profile"
                        f" ({best_bench.recent_points:.1f} pts, {best_bench.recent_opportunities:.1f} opps)."
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

