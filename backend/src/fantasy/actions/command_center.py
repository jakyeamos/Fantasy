from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import duckdb

from fantasy.actions.models import (
    CommandAction,
    CommandCenterResponse,
    CommandUrgency,
    DataRefreshAction,
    MoveCoverage,
    TradeSuggestion,
)
from fantasy.actions.manager_actions import build_manager_actions
from fantasy.actions.portfolio_risk import portfolio_player_risk
from fantasy.actions.ranking import action_sort_key
from fantasy.actions.rookie_actions import build_rookie_actions
from fantasy.actions.trade_suggestions import TradeSuggestionBuilder
from fantasy.actions.weekly_risk import build_weekly_risk_action
from fantasy.context.constants import SIMILAR_PLAYER_EVIDENCE_DOMAINS
from fantasy.context.models import FreshnessTag
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.edge_radar.engine import EdgeRadarEngine
from fantasy.edge_radar.models import EdgeRadarItem
from fantasy.portfolio.portfolio_repo import PortfolioRepo
from fantasy.trends.models import OpportunityFeedItem
from fantasy.trends.opportunity_engine import OpportunityEngine
from fantasy.waiver.models import WaiverRecommendation
from fantasy.waiver.waiver_engine import WaiverEngine
from fantasy.waiver.waiver_repo import WaiverRepo
from fantasy.weekly.models import LineupGapDecision, StartSitDecision, WeeklyPlayerSignal
from fantasy.weekly.weekly_edge_service import WeeklyEdgeService

WEEKLY_DOMAINS = ["injuries", "usage", "schedule", "waivers", "market", "stats"]
COMMAND_CENTER_FRESHNESS_DOMAINS = WEEKLY_DOMAINS + SIMILAR_PLAYER_EVIDENCE_DOMAINS
SELL_EDGE_SIGNALS = {"sell_high", "sell_low"}
MOVE_LANE_SPECS = (
    ("start_sit", "Start/sit", {"lineup"}, "No ranked start/sit or lineup-risk action from weekly data."),
    ("waiver", "Waiver", {"waiver"}, "No ranked waiver add/drop/FAAB action from cached boards."),
    ("trade", "Trade", {"trade"}, "No ranked buy/sell trade action from market or roster fit."),
    ("rookie", "Rookie", {"rookie_pick"}, "No active rookie/draft pick action found."),
    ("portfolio", "Portfolio", {"portfolio"}, "No ranked portfolio exposure or hedge action found."),
    ("manager", "Manager", {"manager"}, "No high-evidence manager exploit action found."),
)


def _similar_player_stale_evidence(stale_domains: list[str]) -> list[str]:
    if not stale_domains:
        return []
    return [
        "Similar-player evidence stale: refresh "
        + ", ".join(stale_domains)
        + " before relying on comps."
    ]


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
        actions.extend(self._edge_radar_actions(league_id, user_rosters))
        actions.extend(self._opportunity_actions(league_id))
        actions.extend(
            build_manager_actions(self._conn, user_rosters, self._league_name)
        )
        actions.extend(build_rookie_actions(self._conn, user_rosters))
        actions.extend(self._portfolio_actions())

        actions.sort(key=action_sort_key)
        ranked = [
            action.model_copy(update={"priority_rank": index + 1})
            for index, action in enumerate(actions[:20])
        ]
        data_health = self._data_health(user_rosters)
        return CommandCenterResponse(
            actions=ranked,
            move_coverage=self._move_coverage(ranked),
            data_health=data_health,
            refresh_actions=self._refresh_actions(user_rosters, data_health),
            total=len(actions),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    def recompute(self) -> CommandCenterResponse:
        for roster in self._user_rosters(None):
            league_id = str(roster["league_id"])
            roster_id = int(roster["roster_id"])
            result = WaiverEngine(self._conn).compute_recommendations(league_id, roster_id)
            self._waiver_repo.upsert_waiver_recommendations(result)
            self._freshness.mark_refreshed(
                league_id,
                "waivers",
                "Command Center waiver board recomputed.",
            )
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
        for domain in COMMAND_CENTER_FRESHNESS_DOMAINS:
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

    def _refresh_actions(
        self,
        rosters: list[dict[str, object]],
        data_health: list[FreshnessTag],
    ) -> list[DataRefreshAction]:
        league_ids = sorted({str(roster["league_id"]) for roster in rosters})
        if not league_ids:
            return []
        stale_domains = {tag.domain for tag in data_health if tag.is_stale}
        actions: list[DataRefreshAction] = []
        for league_id in league_ids:
            if stale_domains.intersection({"injuries", "schedule", "stats", "usage"}):
                actions.append(
                    DataRefreshAction(
                        id=f"weekly-context:{league_id}",
                        domain="weekly_context",
                        league_id=league_id,
                        label=f"Refresh weekly context for {self._league_name(league_id)}",
                        description=(
                            "Updates schedule, injury/status, usage, and weekly stat freshness "
                            "for start/sit and waiver-dependent recommendations."
                        ),
                        endpoint=f"/weekly/league/{league_id}/refresh-context",
                    )
                )
            if "market" in stale_domains:
                actions.append(
                    DataRefreshAction(
                        id=f"market:{league_id}",
                        domain="market",
                        league_id=league_id,
                        label=f"Refresh market for {self._league_name(league_id)}",
                        description="Pulls the current free FantasyCalc ADP baseline for this league format.",
                        endpoint=f"/ingest/adp-baseline/refresh?league_id={league_id}",
                    )
                )
        if "waivers" in stale_domains:
            actions.insert(
                0,
                DataRefreshAction(
                    id="waivers:all",
                    domain="waivers",
                    league_id=None,
                    label="Recompute waiver boards",
                    description="Rebuilds cached add/drop/FAAB recommendations for tracked rosters.",
                    endpoint="/actions/recompute",
                ),
            )
        if "player_metadata" in stale_domains:
            actions.append(
                DataRefreshAction(
                    id="player-metadata:global",
                    domain="player_metadata",
                    league_id=None,
                    label="Refresh player metadata",
                    description=(
                        "Rebuilds dense player role, usage, and market metadata for "
                        "similar-player evidence."
                    ),
                    endpoint="/ingest/player-metadata/refresh",
                )
            )
        if "team_context" in stale_domains:
            actions.append(
                DataRefreshAction(
                    id="team-context:global",
                    domain="team_context",
                    league_id=None,
                    label="Refresh team context",
                    description=(
                        "Reloads team environment, staff, and system context used by "
                        "Edge Radar comparisons."
                    ),
                    endpoint="/ingest/team-context/refresh",
                )
            )
        return actions[:8]

    def _move_coverage(self, actions: list[CommandAction]) -> list[MoveCoverage]:
        coverage: list[MoveCoverage] = []
        for lane, label, categories, missing_reason in MOVE_LANE_SPECS:
            matching = [action for action in actions if action.category in categories]
            if matching:
                first = matching[0]
                coverage.append(
                    MoveCoverage(
                        lane=lane,
                        label=label,
                        status="ready",
                        action_count=len(matching),
                        top_action_id=first.id,
                        reason=f"{label} lane has {len(matching)} ranked action{'s' if len(matching) != 1 else ''}.",
                    )
                )
                continue
            coverage.append(
                MoveCoverage(
                    lane=lane,
                    label=label,
                    status="missing",
                    action_count=0,
                    top_action_id=None,
                    reason=missing_reason,
                )
            )
        return coverage

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

            rec = self._first_roster_legal_waiver_rec(
                league_id,
                roster_id,
                cached.recommendations,
            )
            if rec is None:
                continue
            edge = WeeklyEdgeService(self._conn).build(league_id, roster_id)
            matching_gap = self._matching_lineup_gap(edge.lineup_gaps, rec.position)
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
            stale = set(
                self._stale_domains(league_id) if cached.data_freshness_warning else []
            )
            if matching_gap is not None:
                stale.update(matching_gap.stale_domains)
            evidence = [
                f"Roster fit: {rec.roster_fit}",
                f"Immediate starter: {'yes' if rec.is_immediate_start else 'no'}",
            ]
            why_now = rec.rationale
            urgency = "today" if rec.urgency == "High" else "this_week"
            if matching_gap is not None:
                evidence.append(
                    "Weekly lineup gap: "
                    f"{matching_gap.position} is {matching_gap.gap_to_title_target:.1f} "
                    "below the title target"
                )
                why_now = (
                    f"{rec.rationale} It fixes a current {matching_gap.position} lineup gap: "
                    f"{matching_gap.current_player_name} is "
                    f"{matching_gap.gap_to_title_target:.1f} below the title target."
                )
                if rec.is_immediate_start and matching_gap.urgency in {"today", "this_week"}:
                    urgency = "today"
            actions.append(
                CommandAction(
                    id=f"waiver:{league_id}:{roster_id}:{rec.player_id}",
                    league_id=league_id,
                    roster_id=roster_id,
                    category="waiver",
                    priority_rank=len(actions) + 1,
                    urgency=urgency,
                    confidence=rec.confidence,
                    headline=f"{self._league_name(league_id)}: add {rec.player_name}",
                    recommended_action=f"Claim {rec.player_name} for {bid}.{drop}",
                    acceptable_price=bid,
                    timing=(
                        "Before the waiver run."
                        if rec.recommendation_label != "free_agent_only"
                        else "Add before the next roster churn window."
                    ),
                    why_now=why_now,
                    risk_if_wrong=rec.drop_reason
                    or "The player is only a depth upgrade and may not beat your bench alternative.",
                    evidence=evidence,
                    cta_label="Open Waiver Board",
                    cta_destination=f"/league/{league_id}/waivers?rosterId={roster_id}",
                    stale_domains=sorted(stale),
                )
            )
        return actions

    def _first_roster_legal_waiver_rec(
        self,
        league_id: str,
        roster_id: int,
        recommendations: list[WaiverRecommendation],
    ) -> WaiverRecommendation | None:
        waiver_engine = WaiverEngine(self._conn)
        _, _, roster_counts = waiver_engine._roster_needs(league_id, roster_id)
        position_limits = waiver_engine._position_limits(league_id)
        return next(
            (
                recommendation
                for recommendation in recommendations
                if position_limits.get(recommendation.position) is None
                or roster_counts.get(recommendation.position, 0)
                < position_limits[recommendation.position]
            ),
            None,
        )

    def _matching_lineup_gap(
        self,
        lineup_gaps: list[LineupGapDecision],
        position: str,
    ) -> LineupGapDecision | None:
        normalized = position.upper()
        return next(
            (
                gap
                for gap in lineup_gaps
                if gap.position.upper() == normalized
                or normalized in {"RB", "WR", "TE"} and gap.position.upper() == "FLEX"
            ),
            None,
        )

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
                signal_by_id = {
                    signal.player_id: signal for signal in edge.player_signals
                }
                start_signal = signal_by_id.get(decision.start_player_id)
                sit_signal = signal_by_id.get(decision.sit_player_id)
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
                        acceptable_price="No asset cost; swap the lineup slot.",
                        timing="Before lineups lock.",
                        why_now=decision.why_now,
                        risk_if_wrong=decision.risk_if_wrong,
                        evidence=self._weekly_start_sit_evidence(
                            decision,
                            start_signal,
                            sit_signal,
                        ),
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
            risk_action = build_weekly_risk_action(
                league_name=self._league_name(league_id),
                edge=edge,
                covered_player_ids=set(),
            )
            if risk_action is not None:
                actions.append(risk_action)
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
                        acceptable_price=(
                            "Use a waiver patch or fair trade only; do not overpay past "
                            f"a {gap.gap_to_title_target:.1f}-point title gap."
                        ),
                        timing="This week while the lineup gap is still active.",
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

    def _weekly_start_sit_evidence(
        self,
        decision: StartSitDecision,
        start_signal: WeeklyPlayerSignal | None,
        sit_signal: WeeklyPlayerSignal | None,
    ) -> list[str]:
        evidence = [
            f"Position: {decision.position}",
        ]
        if sit_signal is not None:
            evidence.append(f"Sit availability: {sit_signal.availability_status}")
        evidence.extend(
            [
                f"Projection edge: {decision.edge_points:.1f}",
                f"Start projection: {decision.start_projection:.1f}",
                f"Sit projection: {decision.sit_projection:.1f}",
            ]
        )
        if sit_signal is not None:
            if sit_signal.availability_warning:
                evidence.append(f"Sit risk: {sit_signal.availability_warning}")
            if sit_signal.bye_week_warning:
                evidence.append(f"Sit schedule: {sit_signal.bye_week_warning}")
        if decision.stale_domains:
            evidence.append(
                "Weekly data stale: " + ", ".join(sorted(decision.stale_domains))
            )
        if start_signal is not None:
            if start_signal.usage_note:
                evidence.append(f"Start usage: {start_signal.usage_note}")
            if start_signal.matchup_note:
                evidence.append(f"Start matchup: {start_signal.matchup_note}")
            if start_signal.role_note:
                evidence.append(f"Start role: {start_signal.role_note}")
        return evidence

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

    def _edge_radar_actions(
        self,
        league_id: str | None,
        user_rosters: list[dict[str, object]],
    ) -> list[CommandAction]:
        response = EdgeRadarEngine(self._conn).build(league_id=league_id, limit=8)
        owned_player_ids = self._owned_player_ids_by_league(user_rosters)
        actions: list[CommandAction] = []
        seen_action_ids: set[str] = set()
        seen_player_signals: set[tuple[str, str]] = set()
        for item in response.items[:6]:
            if item.signal_type in SELL_EDGE_SIGNALS and not self._user_owns_edge_player(
                item,
                owned_player_ids,
            ):
                continue
            if item.player_id is not None:
                player_signal_key = (item.signal_type, item.player_id)
                if player_signal_key in seen_player_signals:
                    continue
                seen_player_signals.add(player_signal_key)
            action_id = f"edge:{item.id}"
            if action_id in seen_action_ids:
                continue
            seen_action_ids.add(action_id)
            if item.signal_type == "waiver_pickup":
                category = "waiver"
            elif item.signal_type == "draft_diamond":
                category = "rookie_pick"
            elif item.signal_type in {"portfolio_hedge"}:
                category = "portfolio"
            elif item.signal_type == "manager_exploit":
                category = "manager"
            elif item.signal_type in {"buy_low", "buy_high", "sell_high", "sell_low"}:
                category = "trade"
            else:
                category = "market"
            actions.append(
                CommandAction(
                    id=action_id,
                    league_id=item.league_id,
                    roster_id=item.roster_id,
                    category=category,
                    priority_rank=int(max(1, round(item.conviction_score))),
                    urgency=self._edge_urgency(item),
                    confidence=item.confidence,
                    headline=f"{item.action_label}: {item.player_name}",
                    recommended_action=(
                        f"{item.action_label} {item.player_name}; market delta is "
                        f"{item.market_delta:+.2f}."
                    ),
                    acceptable_price=item.acceptable_price,
                    timing=item.timing_window,
                    why_now=(
                        "Edge Radar ranks this by model/context value versus current market price."
                    ),
                    risk_if_wrong=item.risks[0]
                    if item.risks
                    else "Market delta may be noisy if source freshness is stale.",
                    evidence=(
                        _similar_player_stale_evidence(
                            item.evidence_freshness.stale_domains
                        )
                        + item.source_evidence
                    )[:4],
                    cta_label=item.cta_label,
                    cta_destination=item.cta_destination,
                    stale_domains=item.evidence_freshness.stale_domains,
                )
            )
        return actions

    def _owned_player_ids_by_league(
        self,
        rosters: list[dict[str, object]],
    ) -> dict[str, set[str]]:
        owned_player_ids: dict[str, set[str]] = {}
        for roster in rosters:
            league_id = str(roster["league_id"])
            players = roster.get("players", [])
            if not isinstance(players, list):
                continue
            owned_player_ids[league_id] = {
                str(player_id)
                for player_id in players
                if player_id not in (None, "", 0, "0")
            }
        return owned_player_ids

    def _user_owns_edge_player(
        self,
        item: EdgeRadarItem,
        owned_player_ids: dict[str, set[str]],
    ) -> bool:
        if item.league_id is None or item.player_id is None:
            return False
        return item.player_id in owned_player_ids.get(item.league_id, set())

    def _edge_urgency(self, item: EdgeRadarItem) -> CommandUrgency:
        if abs(item.market_delta) >= 0.25:
            return "today"
        if item.signal_type in {
            "buy_low",
            "buy_high",
            "sell_high",
            "sell_low",
            "waiver_pickup",
        }:
            return "this_week"
        return "watch"

    def _opportunity_action(self, item: OpportunityFeedItem) -> CommandAction | None:
        if item.trend_confidence == "LOW" and item.availability == "available":
            return None

        matching_gap = self._opportunity_lineup_gap(item)
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
        why_now = item.why_summary
        evidence = [
            f"Market gap: {round(item.adp_gap)} startup slots",
            f"Context: {item.availability.replace('_', ' ')}",
        ] + _similar_player_stale_evidence(item.evidence_freshness.stale_domains)
        stale = set(item.evidence_freshness.stale_domains)
        if matching_gap is not None:
            why_now = (
                f"{item.why_summary} It solves a current {matching_gap.position} lineup gap: "
                f"{matching_gap.current_player_name} is "
                f"{matching_gap.gap_to_title_target:.1f} below the title target."
            )
            evidence.append(
                "Weekly lineup gap: "
                f"{matching_gap.position} is {matching_gap.gap_to_title_target:.1f} "
                "below the title target"
            )
            stale.update(matching_gap.stale_domains)
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
            acceptable_price=self._opportunity_price_anchor(item, trade_suggestion),
            timing=(
                "Today while this solves a lineup gap."
                if item.weekly_fit is not None
                else "This week while the market gap is still actionable."
                if item.suggested_action in {"buy", "sell"}
                else "Monitor until price or role moves."
            ),
            why_now=why_now,
            risk_if_wrong=risk,
            evidence=evidence,
            cta_label=item.cta.label if item.cta else "Open Opportunities",
            cta_destination=cta_destination,
            stale_domains=sorted(stale),
            trade_suggestion=trade_suggestion,
        )

    def _opportunity_lineup_gap(
        self,
        item: OpportunityFeedItem,
    ) -> LineupGapDecision | None:
        if (
            item.suggested_action != "buy"
            or item.cta is None
            or item.cta.league_id is None
            or item.cta.user_roster_id is None
        ):
            return None
        edge = WeeklyEdgeService(self._conn).build(
            item.cta.league_id,
            item.cta.user_roster_id,
        )
        return self._matching_lineup_gap(edge.lineup_gaps, item.position)

    def _portfolio_actions(self) -> list[CommandAction]:
        actions: list[CommandAction] = []
        exposure_rows = self._portfolio_repo.load_exposure_rows()
        for row in exposure_rows[:3]:
            if row.league_count < 2:
                continue
            injury_risk = portfolio_player_risk(
                self._conn,
                row.player_id,
                row.full_name,
            )
            actions.append(
                CommandAction(
                    id=f"portfolio:exposure:{row.player_id}",
                    league_id=None,
                    roster_id=None,
                    category="portfolio",
                    priority_rank=row.league_count,
                    urgency=(
                        injury_risk.urgency
                        if injury_risk is not None
                        else "watch" if row.league_count == 2 else "this_week"
                    ),
                    confidence=injury_risk.confidence if injury_risk is not None else "MEDIUM",
                    headline=f"Portfolio exposure: {row.full_name}",
                    recommended_action=(
                        injury_risk.recommended_action
                        if injury_risk is not None
                        else row.hedge_rec
                        or f"Review {row.full_name} across {row.league_count} leagues and decide sell, hold, or hedge."
                    ),
                    acceptable_price=(
                        "Shop or hedge one share; avoid liquidating every exposure below market."
                        if injury_risk is not None
                        else "Hold conviction unless one league offers a market-level hedge."
                    ),
                    timing=(
                        "Today before injury/news exposure compounds."
                        if injury_risk is not None and injury_risk.urgency == "today"
                        else "This week during portfolio review."
                    ),
                    why_now=(
                        injury_risk.why_now
                        if injury_risk is not None
                        else row.urgency_reason
                        or "Repeated exposure turns one injury, role loss, or market correction into a portfolio-level hit."
                    ),
                    risk_if_wrong=(
                        injury_risk.risk_if_wrong
                        if injury_risk is not None
                        else "Selling too much exposure can remove a correct conviction from multiple title paths."
                    ),
                    evidence=[
                        f"Owned in {row.league_count} tracked leagues",
                        f"Position: {row.position}",
                    ]
                    + (injury_risk.evidence if injury_risk is not None else []),
                    cta_label="Open Portfolio",
                    cta_destination=f"/portfolio?playerId={quote_plus(row.player_id)}",
                    stale_domains=(
                        injury_risk.stale_domains if injury_risk is not None else []
                    ),
                )
            )
        return actions

    def _opportunity_price_anchor(
        self,
        item: OpportunityFeedItem,
        trade_suggestion: TradeSuggestion | None,
    ) -> str:
        if trade_suggestion is not None:
            send = " + ".join(trade_suggestion.send_assets) or "your sell-side asset"
            receive = " + ".join(trade_suggestion.receive_assets) or item.player_name
            return f"Stay near {trade_suggestion.fairness_band}: send {send} for {receive}."
        gap = abs(round(item.adp_gap))
        if item.suggested_action == "buy":
            return f"Buy only if the ask preserves most of the {gap}-slot market discount."
        if item.suggested_action == "sell":
            return f"Shop for a return that captures the {gap}-slot market premium."
        return f"No buy/sell price yet; monitor the {gap}-slot market gap."
