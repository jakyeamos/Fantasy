from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import duckdb

from fantasy.actions.models import CommandAction, CommandCenterResponse
from fantasy.actions.trade_suggestions import TradeSuggestionBuilder
from fantasy.context.models import FreshnessTag
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.portfolio.portfolio_repo import PortfolioRepo
from fantasy.profiling.profiling_repo import ProfilingRepo
from fantasy.trends.models import OpportunityFeedItem
from fantasy.trends.opportunity_engine import OpportunityEngine
from fantasy.waiver.waiver_engine import WaiverEngine
from fantasy.waiver.waiver_repo import WaiverRepo
from fantasy.weekly.weekly_edge_service import WeeklyEdgeService

WEEKLY_DOMAINS = ["injuries", "usage", "schedule", "waivers", "market", "stats"]

URGENCY_WEIGHT = {"today": 0, "this_week": 1, "watch": 2, "low": 3}
CONFIDENCE_WEIGHT = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
CATEGORY_WEIGHT = {
    "waiver": 0,
    "lineup": 1,
    "trade": 2,
    "market": 3,
    "rookie_pick": 4,
    "portfolio": 5,
    "manager": 6,
}


class CommandCenterEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._portfolio_repo = PortfolioRepo(conn)
        self._waiver_repo = WaiverRepo(conn)
        self._freshness = FreshnessService(ContextRepo(conn))
        self._trade_suggestions = TradeSuggestionBuilder(conn)

    def build(self, league_id: str | None = None) -> CommandCenterResponse:
        actions: list[CommandAction] = []
        user_rosters = self._user_rosters(league_id)

        actions.extend(self._waiver_actions(user_rosters))
        actions.extend(self._weekly_actions(user_rosters))
        actions.extend(self._opportunity_actions(league_id))
        actions.extend(self._manager_actions(user_rosters))
        actions.extend(self._portfolio_actions())

        actions.sort(
            key=lambda action: (
                URGENCY_WEIGHT[action.urgency],
                CONFIDENCE_WEIGHT[action.confidence],
                CATEGORY_WEIGHT[action.category],
                action.priority_rank,
                action.headline.lower(),
            )
        )
        ranked = [
            action.model_copy(update={"priority_rank": index + 1})
            for index, action in enumerate(actions[:20])
        ]
        return CommandCenterResponse(
            actions=ranked,
            data_health=self._data_health(user_rosters),
            total=len(actions),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    def recompute(self) -> CommandCenterResponse:
        for roster in self._user_rosters(None):
            league_id = str(roster["league_id"])
            roster_id = int(roster["roster_id"])
            result = WaiverEngine(self._conn).compute_recommendations(league_id, roster_id)
            self._waiver_repo.upsert_waiver_recommendations(result)
        return self.build()

    def _user_rosters(self, league_id: str | None) -> list[dict[str, object]]:
        rows = self._portfolio_repo._portfolio_roster_rows()
        if league_id is None:
            return rows
        return [row for row in rows if str(row["league_id"]) == league_id]

    def _league_name(self, league_id: str) -> str:
        row = self._conn.execute(
            """
            SELECT name
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        return str(row[0]) if row and row[0] else league_id

    def _stale_domains(self, league_id: str) -> list[str]:
        return [
            tag.domain
            for tag in self._freshness.get_tags(league_id, WEEKLY_DOMAINS)
            if tag.is_stale
        ]

    def _data_health(self, rosters: list[dict[str, object]]) -> list[FreshnessTag]:
        league_ids = sorted({str(roster["league_id"]) for roster in rosters})
        if not league_ids:
            return []
        health: list[FreshnessTag] = []
        for domain in WEEKLY_DOMAINS:
            tags = [
                tag
                for league_id in league_ids
                for tag in self._freshness.get_tags(league_id, [domain])
            ]
            stale_count = sum(1 for tag in tags if tag.is_stale)
            last_updated = max(
                (tag.last_updated for tag in tags if tag.last_updated is not None),
                default=None,
            )
            health.append(
                FreshnessTag(
                    domain=domain,
                    last_updated=last_updated,
                    is_stale=stale_count > 0,
                    warning=(
                        f"{stale_count}/{len(league_ids)} tracked leagues stale for {domain}"
                        if stale_count
                        else None
                    ),
                )
            )
        return health

    def _waiver_actions(
        self, rosters: list[dict[str, object]]
    ) -> list[CommandAction]:
        actions: list[CommandAction] = []
        for roster in rosters:
            league_id = str(roster["league_id"])
            roster_id = int(roster["roster_id"])
            cached = self._waiver_repo.get_waiver_recommendations(league_id, roster_id)
            if cached is None or not cached.recommendations:
                continue

            rec = cached.recommendations[0]
            bid = (
                "free claim"
                if rec.recommendation_label == "free_agent_only"
                else f"${rec.bid_low or 0}-${rec.bid_high or 0} FAAB"
            )
            drop = (
                f" Drop {rec.drop_candidate}."
                if rec.drop_candidate
                else " Choose your lowest bench churn asset."
            )
            stale = self._stale_domains(league_id) if cached.data_freshness_warning else []
            actions.append(
                CommandAction(
                    id=f"waiver:{league_id}:{roster_id}:{rec.player_id}",
                    league_id=league_id,
                    roster_id=roster_id,
                    category="waiver",
                    priority_rank=len(actions) + 1,
                    urgency="today" if rec.urgency == "High" else "this_week",
                    confidence=rec.confidence,
                    headline=f"{self._league_name(league_id)}: add {rec.player_name}",
                    recommended_action=f"Claim {rec.player_name} for {bid}.{drop}",
                    why_now=rec.rationale,
                    risk_if_wrong=rec.drop_reason
                    or "The player is only a depth upgrade and may not beat your bench alternative.",
                    evidence=[
                        f"Roster fit: {rec.roster_fit}",
                        f"Immediate starter: {'yes' if rec.is_immediate_start else 'no'}",
                    ],
                    cta_label="Open Waiver Board",
                    cta_destination=f"/league/{league_id}/waivers?rosterId={roster_id}",
                    stale_domains=stale,
                )
            )
        return actions

    def _weekly_actions(
        self, rosters: list[dict[str, object]]
    ) -> list[CommandAction]:
        actions: list[CommandAction] = []
        for roster in rosters:
            league_id = str(roster["league_id"])
            roster_id = int(roster["roster_id"])
            edge = WeeklyEdgeService(self._conn).build(league_id, roster_id)
            if edge.start_sit:
                decision = edge.start_sit[0]
                actions.append(
                    CommandAction(
                        id=f"weekly:start-sit:{league_id}:{roster_id}:{decision.start_player_id}:{decision.sit_player_id}",
                        league_id=league_id,
                        roster_id=roster_id,
                        category="lineup",
                        priority_rank=len(actions) + 1,
                        urgency="today",
                        confidence=decision.confidence,
                        headline=f"{self._league_name(league_id)}: start {decision.start_player_name}",
                        recommended_action=decision.recommendation,
                        why_now=decision.why_now,
                        risk_if_wrong=decision.risk_if_wrong,
                        evidence=[
                            f"Position: {decision.position}",
                            f"Projection edge: {decision.edge_points:.1f}",
                            f"Start projection: {decision.start_projection:.1f}",
                        ],
                        cta_label="Open Weekly Edge",
                        cta_destination=(
                            f"/league/{league_id}?rosterId={roster_id}&focus=weekly"
                            f"&startPlayerId={decision.start_player_id}"
                            f"&sitPlayerId={decision.sit_player_id}"
                        ),
                        stale_domains=decision.stale_domains,
                    )
                )
                continue
            if edge.lineup_gaps:
                gap = edge.lineup_gaps[0]
                actions.append(
                    CommandAction(
                        id=f"weekly:lineup-gap:{league_id}:{roster_id}:{gap.position}",
                        league_id=league_id,
                        roster_id=roster_id,
                        category="lineup",
                        priority_rank=len(actions) + 1,
                        urgency=gap.urgency,
                        confidence=gap.confidence,
                        headline=f"{self._league_name(league_id)}: fix {gap.position}",
                        recommended_action=gap.recommended_action,
                        why_now=gap.why_now,
                        risk_if_wrong="The gap can close if recent usage or injury data is stale.",
                        evidence=[
                            f"Current starter: {gap.current_player_name}",
                            f"Title gap: {gap.gap_to_title_target:.1f}",
                        ],
                        cta_label="Open Weekly Edge",
                        cta_destination=(
                            f"/league/{league_id}?rosterId={roster_id}&focus=weekly"
                            f"&position={quote_plus(gap.position)}"
                        ),
                        stale_domains=gap.stale_domains,
                    )
                )
        return actions

    def _opportunity_actions(self, league_id: str | None) -> list[CommandAction]:
        actions: list[CommandAction] = []
        items = OpportunityEngine(self._conn).build_feed()
        for item in items[:8]:
            if league_id is not None and item.cta and item.cta.league_id != league_id:
                continue
            action = self._opportunity_action(item)
            if action is not None:
                actions.append(action)
        return actions

    def _opportunity_action(self, item: OpportunityFeedItem) -> CommandAction | None:
        if item.trend_confidence == "LOW" and item.availability == "available":
            return None

        cta_destination = "/opportunities"
        if item.cta is not None:
            if item.cta.destination == "trade_evaluator" and item.cta.league_id:
                params = [f"leagueId={item.cta.league_id}"]
                if item.cta.user_roster_id is not None:
                    params.append(f"userRosterId={item.cta.user_roster_id}")
                if item.cta.manager_roster_id is not None:
                    params.append(f"counterpartyRosterId={item.cta.manager_roster_id}")
                params.append(f"targetPlayerId={item.player_id}")
                params.append(f"targetPlayerName={quote_plus(item.player_name)}")
                cta_destination = f"/trades?{'&'.join(params)}"
            elif item.cta.destination == "manager_dossier" and item.cta.league_id:
                cta_destination = f"/league/{item.cta.league_id}/managers"
            elif item.cta.league_id:
                cta_destination = f"/league/{item.cta.league_id}/rankings"

        verb = {"buy": "Buy", "sell": "Shop", "hold": "Hold"}[item.suggested_action]
        urgency = "today" if item.suggested_action in {"buy", "sell"} else "watch"
        risk = (
            item.conflict_explanation
            or "The market gap may be noisy if league mates do not value this player near public ADP."
        )
        trade_suggestion = (
            self._trade_suggestions.build(item)
            if item.suggested_action in {"buy", "sell"}
            else None
        )
        if trade_suggestion is not None:
            cta_destination = self._trade_suggestions.destination(item, trade_suggestion)
        return CommandAction(
            id=f"market:{item.player_id}",
            league_id=item.cta.league_id if item.cta else None,
            roster_id=item.cta.user_roster_id if item.cta else None,
            category="trade" if item.suggested_action in {"buy", "sell"} else "market",
            priority_rank=int(max(1, round(item.impact_score))),
            urgency=urgency,
            confidence=item.trend_confidence,
            headline=f"{verb} window: {item.player_name}",
            recommended_action=f"{verb} {item.player_name}; use the market gap as the price anchor.",
            why_now=item.why_summary,
            risk_if_wrong=risk,
            evidence=[
                f"Market gap: {round(item.adp_gap)} startup slots",
                f"Context: {item.availability.replace('_', ' ')}",
            ],
            cta_label=item.cta.label if item.cta else "Open Opportunities",
            cta_destination=cta_destination,
            trade_suggestion=trade_suggestion,
        )

    def _manager_actions(
        self, rosters: list[dict[str, object]]
    ) -> list[CommandAction]:
        actions: list[CommandAction] = []
        for roster in rosters:
            league_id = str(roster["league_id"])
            user_roster_id = int(roster["roster_id"])
            summaries = ProfilingRepo(self._conn).list_manager_summaries(league_id)
            strong = [
                summary
                for summary in summaries
                if summary.roster_id != user_roster_id
                and not summary.low_confidence
                and summary.evidence_count >= 3
                and summary.top_pitch_angle is not None
            ]
            if not strong:
                continue
            summary = strong[0]
            angle = summary.top_pitch_angle
            if angle is None:
                continue
            actions.append(
                CommandAction(
                    id=f"manager:{league_id}:{summary.roster_id}",
                    league_id=league_id,
                    roster_id=user_roster_id,
                    category="manager",
                    priority_rank=len(actions) + 1,
                    urgency="this_week",
                    confidence="HIGH" if summary.evidence_count >= 5 else "MEDIUM",
                    headline=f"Pitch {summary.manager_name} in {self._league_name(league_id)}",
                    recommended_action=(
                        f"Open with {angle.send_description}; avoid {angle.avoid_description}."
                    ),
                    why_now=angle.reasoning,
                    risk_if_wrong=(
                        "Manager tendency samples can age quickly if recent trades changed their build."
                    ),
                    evidence=[
                        f"Evidence count: {summary.evidence_count}",
                        f"Exploitability: {round(summary.exploitability_score)}",
                    ],
                    cta_label="Open Managers",
                    cta_destination=f"/league/{league_id}/managers",
                )
            )
        return actions

    def _portfolio_actions(self) -> list[CommandAction]:
        actions: list[CommandAction] = []
        exposure_rows = self._portfolio_repo.load_exposure_rows()
        for row in exposure_rows[:3]:
            if row.league_count < 2:
                continue
            actions.append(
                CommandAction(
                    id=f"portfolio:exposure:{row.player_id}",
                    league_id=None,
                    roster_id=None,
                    category="portfolio",
                    priority_rank=row.league_count,
                    urgency="watch" if row.league_count == 2 else "this_week",
                    confidence="MEDIUM",
                    headline=f"Portfolio exposure: {row.full_name}",
                    recommended_action=(
                        row.hedge_rec
                        or f"Review {row.full_name} across {row.league_count} leagues and decide sell, hold, or hedge."
                    ),
                    why_now=(
                        row.urgency_reason
                        or "Repeated exposure turns one injury, role loss, or market correction into a portfolio-level hit."
                    ),
                    risk_if_wrong=(
                        "Selling too much exposure can remove a correct conviction from multiple title paths."
                    ),
                    evidence=[
                        f"Owned in {row.league_count} tracked leagues",
                        f"Position: {row.position}",
                    ],
                    cta_label="Open Portfolio",
                    cta_destination=f"/portfolio?playerId={quote_plus(row.player_id)}",
                )
            )
        return actions
