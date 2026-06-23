from __future__ import annotations

import json
from typing import Any, Literal

import duckdb

from fantasy.context.calendar_service import CalendarService
from fantasy.context.context_repo import ContextRepo
from fantasy.intelligence.constants import CONTENDER_DIRECTION_LABELS
from fantasy.portfolio.portfolio_repo import PortfolioRepo
from fantasy.trends.constants import CALENDAR_ESCALATION_LABELS, OPPORTUNITY_GAP_THRESHOLD
from fantasy.trends.models import OpportunityCta, OpportunityFeedItem
from fantasy.trends.models import confidence_multiplier
from fantasy.trends.similarity import find_similar_players
from fantasy.trends.trend_engine import TrendEngine
from fantasy.trends.trend_repo import TrendRepo

MarketRecommendation = Literal[
    "buy_low",
    "sell_high",
    "hold_despite_weak_market",
    "hold_despite_strong_market",
    "hold",
]


def is_conflict(market_recommendation: str, trend_label: str) -> bool:
    if market_recommendation in {"buy_low", "hold_despite_weak_market"}:
        return trend_label == "will_fall"
    if market_recommendation in {"sell_high", "hold_despite_strong_market"}:
        return trend_label == "will_rise"
    return False


class OpportunityEngine:
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        trend_engine: TrendEngine | None = None,
        calendar_service: CalendarService | None = None,
    ) -> None:
        self._conn = conn
        self._repo = TrendRepo(conn)
        self._trend_engine = trend_engine or TrendEngine(conn)
        self._calendar_service = calendar_service or CalendarService(ContextRepo(conn))
        self._portfolio_repo = PortfolioRepo(conn)

    def build_feed(self) -> list[OpportunityFeedItem]:
        user_rosters = self._portfolio_repo._portfolio_roster_rows()
        if not user_rosters:
            user_rosters = self._fallback_user_rosters()
        owned_map = self._owned_map(user_rosters)
        roster_contexts = self._roster_contexts(user_rosters)
        contender_leagues = self._contender_league_ids(user_rosters)
        calendar_state = (
            self._calendar_service.active_state(user_rosters[0]["league_id"])
            if user_rosters
            else self._calendar_service.active_state("")
        )
        escalation_label = CALENDAR_ESCALATION_LABELS.get(calendar_state)

        items: list[OpportunityFeedItem] = []
        for candidate in self._repo.list_candidate_players():
            player_id = str(candidate["player_id"])
            snapshot = self._trend_engine.current_snapshot(player_id)
            if snapshot is None:
                continue

            startup_adp = candidate.get("startup_adp") or snapshot.get("startup_adp")
            if startup_adp is None:
                continue

            trend = self._trend_engine.compute_trend(player_id)
            expected_adp = self._expected_adp(snapshot)
            adp_gap = round(expected_adp - float(startup_adp), 2)
            if abs(adp_gap) < OPPORTUNITY_GAP_THRESHOLD:
                continue

            market_recommendation = self._market_recommendation(adp_gap)
            suggested_action = self._suggested_action(
                adp_gap=adp_gap,
                trend_label=trend.trend_label,
                age=int(snapshot.get("age") or candidate.get("age") or 24),
                contender_leagues=contender_leagues,
            )
            conflict_explanation = None
            if is_conflict(market_recommendation, trend.trend_label):
                conflict_explanation = self._conflict_explanation(
                    player_name=str(candidate.get("full_name") or player_id),
                    market_recommendation=market_recommendation,
                    trend_label=trend.trend_label,
                )

            impact_score = abs(adp_gap) * confidence_multiplier(trend.confidence)
            if escalation_label is not None:
                impact_score *= 1.1

            owned_in_leagues = owned_map.get(player_id, [])
            cta = self._cta_for_player(
                player_id=player_id,
                suggested_action=suggested_action,
                user_rosters=user_rosters,
                roster_contexts=roster_contexts,
            )
            items.append(
                OpportunityFeedItem(
                    player_id=player_id,
                    player_name=str(candidate.get("full_name") or player_id),
                    position=str(candidate.get("position") or snapshot.get("position") or "UNKNOWN"),
                    trend_label=trend.trend_label,
                    trend_confidence=trend.confidence,
                    adp_gap=adp_gap,
                    suggested_action=suggested_action,
                    impact_score=round(impact_score, 2),
                    why_summary=self._why_summary(
                        player_name=str(candidate.get("full_name") or player_id),
                        adp_gap=adp_gap,
                        suggested_action=suggested_action,
                        trend_label=trend.trend_label,
                        contender_fit=bool(
                            suggested_action == "buy"
                            and trend.trend_label == "will_fall"
                            and int(snapshot.get("age") or 24) >= 28
                            and bool(contender_leagues)
                        ),
                    ),
                    owned_in_leagues=owned_in_leagues,
                    similar_players=find_similar_players(player_id, self._conn),
                    conflict_explanation=conflict_explanation,
                    calendar_escalated=escalation_label is not None,
                    calendar_escalation_label=escalation_label,
                    cta=cta,
                )
            )

        items.sort(
            key=lambda item: (
                -item.impact_score,
                item.player_name.lower(),
                item.player_id,
            )
        )
        return items

    def _contender_league_ids(self, user_rosters: list[dict[str, object]]) -> set[str]:
        contender_leagues: set[str] = set()
        for roster in user_rosters:
            row = self._conn.execute(
                """
                SELECT primary_label
                FROM team_directions
                WHERE league_id = ? AND roster_id = ?
                LIMIT 1
                """,
                [roster["league_id"], roster["roster_id"]],
            ).fetchone()
            if row and str(row[0]) in CONTENDER_DIRECTION_LABELS:
                contender_leagues.add(str(roster["league_id"]))
        return contender_leagues

    def _fallback_user_rosters(self) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT league_id, roster_id, players
            FROM rosters
            ORDER BY league_id, roster_id
            """
        ).fetchall()
        per_league: dict[str, dict[str, object]] = {}
        for league_id, roster_id, players_json in rows:
            league_key = str(league_id)
            if league_key in per_league:
                continue
            per_league[league_key] = {
                "league_id": league_key,
                "roster_id": int(roster_id),
                "players": self._loads(players_json),
            }
        return list(per_league.values())

    def _owned_map(self, user_rosters: list[dict[str, object]]) -> dict[str, list[str]]:
        owned: dict[str, set[str]] = {}
        for roster in user_rosters:
            league_id = str(roster["league_id"])
            for player_id in self._loads(roster.get("players")):
                owned.setdefault(player_id, set()).add(league_id)
        return {
            player_id: sorted(leagues)
            for player_id, leagues in owned.items()
        }

    def _roster_contexts(
        self,
        user_rosters: list[dict[str, object]],
    ) -> dict[str, list[dict[str, object]]]:
        user_roster_by_league = {
            str(roster["league_id"]): int(roster["roster_id"])
            for roster in user_rosters
        }
        if not user_roster_by_league:
            return {}

        rows = self._conn.execute(
            """
            SELECT league_id, roster_id, players
            FROM rosters
            WHERE league_id IN (SELECT UNNEST(?))
            ORDER BY league_id, roster_id
            """,
            [list(user_roster_by_league.keys())],
        ).fetchall()
        contexts: dict[str, list[dict[str, object]]] = {}
        for league_id, roster_id, players_json in rows:
            league_key = str(league_id)
            roster_key = int(roster_id)
            for player_id in self._loads(players_json):
                contexts.setdefault(player_id, []).append(
                    {
                        "league_id": league_key,
                        "roster_id": roster_key,
                        "user_roster_id": user_roster_by_league[league_key],
                        "is_user_roster": roster_key == user_roster_by_league[league_key],
                    }
                )
        return contexts

    def _cta_for_player(
        self,
        *,
        player_id: str,
        suggested_action: str,
        user_rosters: list[dict[str, object]],
        roster_contexts: dict[str, list[dict[str, object]]],
    ) -> OpportunityCta | None:
        contexts = roster_contexts.get(player_id, [])
        user_contexts = [context for context in contexts if bool(context["is_user_roster"])]
        opponent_contexts = [context for context in contexts if not bool(context["is_user_roster"])]

        if suggested_action == "sell" and user_contexts:
            context = user_contexts[0]
            return self._trade_cta(
                label="Shop in Trade Evaluator",
                context=context,
                target_player_roster_id=int(context["roster_id"]),
            )

        if suggested_action == "buy":
            if opponent_contexts:
                context = opponent_contexts[0]
                return self._trade_cta(
                    label="Build Buy Offer",
                    context=context,
                    target_player_roster_id=int(context["roster_id"]),
                    manager_roster_id=int(context["roster_id"]),
                )
            if user_rosters:
                roster = user_rosters[0]
                return OpportunityCta(
                    label="Find League Fit",
                    destination="player_rankings",
                    league_id=str(roster["league_id"]),
                    user_roster_id=int(roster["roster_id"]),
                )

        if opponent_contexts:
            context = opponent_contexts[0]
            return OpportunityCta(
                label="View Manager",
                destination="manager_dossier",
                league_id=str(context["league_id"]),
                user_roster_id=int(context["user_roster_id"]),
                manager_roster_id=int(context["roster_id"]),
                target_player_roster_id=int(context["roster_id"]),
            )

        if user_contexts:
            context = user_contexts[0]
            return OpportunityCta(
                label="View Ranking",
                destination="player_rankings",
                league_id=str(context["league_id"]),
                user_roster_id=int(context["user_roster_id"]),
                target_player_roster_id=int(context["roster_id"]),
            )

        if user_rosters:
            roster = user_rosters[0]
            return OpportunityCta(
                label="View Rankings",
                destination="player_rankings",
                league_id=str(roster["league_id"]),
                user_roster_id=int(roster["roster_id"]),
            )

        return None

    def _trade_cta(
        self,
        *,
        label: str,
        context: dict[str, Any],
        target_player_roster_id: int,
        manager_roster_id: int | None = None,
    ) -> OpportunityCta:
        return OpportunityCta(
            label=label,
            destination="trade_evaluator",
            league_id=str(context["league_id"]),
            user_roster_id=int(context["user_roster_id"]),
            manager_roster_id=manager_roster_id,
            target_player_roster_id=target_player_roster_id,
        )

    def _loads(self, raw: object) -> list[str]:
        if raw is None:
            return []
        if isinstance(raw, list):
            values = raw
        else:
            try:
                values = json.loads(str(raw))
            except json.JSONDecodeError:
                return []
        return [str(value) for value in values if value not in (None, "", 0, "0")]

    def _expected_adp(self, snapshot: dict[str, object]) -> float:
        quality = (
            0.16 * float(snapshot.get("comp_current_production") or 0.0)
            + 0.18 * float(snapshot.get("comp_short_term") or 0.0)
            + 0.10 * float(snapshot.get("comp_role_stability") or 0.0)
            + 0.16 * float(snapshot.get("comp_age_curve") or 0.0)
            + 0.10 * float(snapshot.get("comp_insulation") or 0.0)
            + 0.08 * float(snapshot.get("comp_market_liquidity") or 0.0)
            + 0.06 * float(snapshot.get("comp_positional_scarcity") or 0.0)
            - 0.08 * float(snapshot.get("comp_fragility") or 0.0)
            + 0.05 * float(snapshot.get("comp_ceiling") or 0.0)
            + 0.05 * float(snapshot.get("comp_floor") or 0.0)
            + 0.04 * float(snapshot.get("comp_rerollability") or 0.0)
            + 0.02 * float(snapshot.get("comp_contract") or 0.0)
        )
        quality = max(0.0, min(1.0, quality))
        return round(200.0 - (quality * 199.0), 2)

    def _market_recommendation(self, adp_gap: float) -> MarketRecommendation:
        if adp_gap <= -OPPORTUNITY_GAP_THRESHOLD:
            return "buy_low"
        if adp_gap >= OPPORTUNITY_GAP_THRESHOLD:
            return "sell_high"
        if adp_gap < 0:
            return "hold_despite_weak_market"
        if adp_gap > 0:
            return "hold_despite_strong_market"
        return "hold"

    def _suggested_action(
        self,
        *,
        adp_gap: float,
        trend_label: str,
        age: int,
        contender_leagues: set[str],
    ) -> Literal["buy", "sell", "hold"]:
        if trend_label == "will_fall" and adp_gap > 0:
            return "sell"
        if trend_label == "will_rise" and adp_gap < 0:
            return "buy"
        if (
            trend_label == "will_fall"
            and adp_gap < 0
            and age >= 28
            and contender_leagues
        ):
            return "buy"
        return "hold"

    def _why_summary(
        self,
        *,
        player_name: str,
        adp_gap: float,
        suggested_action: str,
        trend_label: str,
        contender_fit: bool,
    ) -> str:
        gap_slots = int(round(abs(adp_gap)))
        if suggested_action == "sell":
            return (
                f"{player_name} sits about {gap_slots} startup slots above the model, "
                "and the component trend still points down."
            )
        if contender_fit:
            return (
                f"{player_name} carries a decline signal, but the market discount is steep "
                "enough to justify a short-window contender buy."
            )
        if suggested_action == "buy":
            return (
                f"{player_name} is discounted by roughly {gap_slots} startup slots while "
                "the component trend still points up."
            )
        if trend_label == "will_rise":
            return (
                f"The market premium is real, but {player_name}'s component profile still "
                "projects upward movement next season."
            )
        return (
            f"{player_name} shows a sizable market gap, but the trend signal argues for "
            "patience instead of an immediate buy or sell."
        )

    def _conflict_explanation(
        self,
        *,
        player_name: str,
        market_recommendation: MarketRecommendation,
        trend_label: str,
    ) -> str:
        market_copy = {
            "buy_low": "The market gap says buy low",
            "sell_high": "The market gap says sell high",
            "hold_despite_weak_market": "The market discount is real",
            "hold_despite_strong_market": "The market premium is real",
            "hold": "The market signal is neutral",
        }[market_recommendation]
        trend_copy = {
            "will_rise": "component trajectories still project a rise",
            "will_maintain": "component trajectories project stability",
            "will_fall": "component trajectories project a fall",
        }[trend_label]
        return f"{market_copy} for {player_name}, but {trend_copy} next season."
