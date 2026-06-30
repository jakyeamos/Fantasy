from __future__ import annotations

import logging
from typing import Any

import duckdb

from fantasy.intelligence.constants import REBUILD_DIRECTION_LABELS
from fantasy.intelligence.positional_context import PositionalContext
from fantasy.recommendation.card_engine import RecommendationCardEngine
from fantasy.trade.constants import (
    DIRECTION_ADVANCING_THRESHOLD,
    DIRECTION_NEGATIVE_THRESHOLD,
    MARKET_FAIR_THRESHOLD,
    PICK_MARKET_VALUES,
)
from fantasy.trade.models import (
    DimensionScore,
    StrategicDistinction,
    ThirdPartyTradeEvaluation,
    TradeBalance,
    TradeAsset,
    TradeEvaluation,
    TradeRequest,
)
from fantasy.trade.trade_repo import TradeRepo

logger = logging.getLogger(__name__)


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _asset_market_value(value: dict[str, Any]) -> float:
    return max(float(value.get("lens_market") or 0.0), 0.0)


def _lens_value(value: dict[str, Any], key: str, fallback: float) -> float:
    raw = value.get(key)
    return fallback if raw is None else max(float(raw), 0.0)


def _asset_context_value(value: dict[str, Any]) -> float:
    market = _asset_market_value(value)
    return (
        market * 0.35
        + _lens_value(value, "lens_team_fit", market) * 0.20
        + _lens_value(value, "lens_direction", market) * 0.15
        + _lens_value(value, "lens_insulation", market) * 0.12
        + _lens_value(value, "lens_production", market) * 0.08
        + _lens_value(value, "comp_positional_scarcity", market) * 0.06
        + _lens_value(value, "comp_market_liquidity", market) * 0.04
    )


class TradeEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = TradeRepo(conn)
        self._card_engine = RecommendationCardEngine(conn)
        self._degradation_reasons: list[str] = []

    def _record_degradation(self, reason: str, log_message: str) -> None:
        if reason not in self._degradation_reasons:
            self._degradation_reasons.append(reason)
        logger.warning(log_message)

    def _extract_player_ids(self, assets: list[TradeAsset]) -> list[str]:
        return [
            str(asset.player_id)
            for asset in assets
            if asset.asset_type == "player" and asset.player_id is not None
        ]

    def _build_pick_proxy(
        self,
        asset: TradeAsset,
        direction_label: str | None,
        league_id: str | None = None,
        target_roster_id: int | None = None,
    ) -> dict[str, Any]:
        fallback_reason: str | None = None
        pick_label = f"{asset.pick_year or 'unknown'} round {asset.pick_round or 'unknown'}"
        if (
            league_id is not None
            and asset.pick_owner_roster_id is not None
            and asset.pick_year is not None
            and asset.pick_round is not None
        ):
            try:
                pick_value = self._repo.get_pick_value(
                    asset,
                    league_id,
                    target_roster_id=target_roster_id,
                )
                demand_value = max(float(pick_value.demand_adjusted_value), 0.01)
                league_value = max(float(pick_value.league_adjusted_value), 0.01)
                normalized_market = min(demand_value / 100.0, 1.0)
                normalized_league = min(league_value / 100.0, 1.0)
                return {
                    "player_id": None,
                    "full_name": f"{asset.pick_year} Round {asset.pick_round}",
                    "position": "PICK",
                    "comp_insulation": min(normalized_league + 0.1, 1.0),
                    "comp_market_liquidity": min(normalized_market + 0.1, 1.0),
                    "comp_age_curve": 1.0,
                    "comp_positional_scarcity": normalized_league,
                    "comp_short_term": min(pick_value.timed_value / 100.0, 1.0),
                    "lens_market": normalized_market,
                    "lens_insulation": min(normalized_league + 0.05, 1.0),
                    "lens_team_fit": normalized_league,
                    "lens_direction": normalized_market,
                    "lens_production": 0.0,
                    "pick_value": pick_value,
                }
            except Exception as exc:
                fallback_reason = (
                    f"pick_valuation_fallback: {pick_label} valued with static market table "
                    f"because {exc}"
                )
                self._record_degradation(
                    fallback_reason,
                    "pick valuation unavailable for %s in league %s; using static pick fallback: %s"
                    % (pick_label, league_id, exc),
                )
        else:
            fallback_reason = (
                f"pick_valuation_fallback: {pick_label} valued with static market table "
                "because required pick identity is incomplete"
            )
            self._record_degradation(
                fallback_reason,
                "pick valuation unavailable for %s; using static pick fallback because required pick identity is incomplete"
                % pick_label,
            )

        base = PICK_MARKET_VALUES.get(int(asset.pick_round or 4), 0.05)
        direction_bonus = 0.25 if direction_label in REBUILD_DIRECTION_LABELS else -0.10
        proxy = {
            "player_id": None,
            "full_name": f"{asset.pick_year} Round {asset.pick_round}",
            "position": "PICK",
            "comp_insulation": base,
            "comp_market_liquidity": min(base + 0.15, 1.0),
            "comp_age_curve": 1.0,
            "comp_positional_scarcity": base,
            "comp_short_term": 0.15,
            "lens_market": base,
            "lens_insulation": base,
            "lens_team_fit": 0.45,
            "lens_direction": max(0.0, min(1.0, 0.55 + direction_bonus)),
            "lens_production": 0.0,
            "valuation_source": "static_pick_fallback",
        }
        if fallback_reason is not None:
            proxy["degradation_reason"] = fallback_reason
        return proxy

    def _score_third_party_trades(
        self,
        request: TradeRequest,
    ) -> list[ThirdPartyTradeEvaluation]:
        third_party_trades = request.third_party_trades or []
        if not third_party_trades:
            return []

        evaluations: list[ThirdPartyTradeEvaluation] = []
        for leg in third_party_trades:
            sends_resolved = self._resolve_assets(
                leg.sends, request.league_id, leg.roster_id, None
            )
            receives_resolved = self._resolve_assets(
                leg.receives, request.league_id, leg.roster_id, None
            )
            sent_val = sum(float(v.get("lens_market") or 0.0) for v in sends_resolved)
            recv_val = sum(float(v.get("lens_market") or 0.0) for v in receives_resolved)
            baseline = max(sent_val, recv_val, 0.01)
            net = recv_val - sent_val
            score = _clamp_score(50.0 + (net / baseline) * 50.0)
            confidence = (
                "HIGH"
                if all(
                    value.get("lens_market") is not None
                    for value in sends_resolved + receives_resolved
                )
                else "LOW"
            )
            direction = "receives" if net > 0 else "sends away" if net < 0 else "breaks even on"
            reasoning = (
                f"Roster {leg.roster_id} {direction} "
                f"{abs(round((net / baseline) * 100, 1))}% net market value in its sidecar leg."
                if net != 0
                else f"Roster {leg.roster_id} is roughly even on sidecar market value."
            )
            evaluations.append(
                ThirdPartyTradeEvaluation(
                    roster_id=leg.roster_id,
                    sent_market_value=round(sent_val, 4),
                    received_market_value=round(recv_val, 4),
                    net_market_delta=round(net, 4),
                    market_fairness=DimensionScore(
                        score=score,
                        confidence=confidence,
                        reasoning=reasoning,
                    ),
                )
            )
        return evaluations

    def _apply_multi_team_context(
        self,
        third_party_evaluations: list[ThirdPartyTradeEvaluation],
        dimensions: list[DimensionScore],
    ) -> None:
        if not third_party_evaluations:
            return

        max_imbalance = max(
            abs(evaluation.market_fairness.score - 50.0) * 2.0
            for evaluation in third_party_evaluations
        )
        sidecar_note = " ".join(
            evaluation.market_fairness.reasoning
            for evaluation in third_party_evaluations
        )
        note = (
            f" Multi-team context: {len(third_party_evaluations)} third-party leg(s) scored. "
            f"{sidecar_note} Primary dimensions still score your net swap, and participant "
            "sidecars feed reroute and package explanations."
        )
        for dimension in dimensions:
            if max_imbalance > 25:
                if dimension.confidence == "HIGH":
                    dimension.confidence = "MEDIUM"
                elif dimension.confidence == "MEDIUM":
                    dimension.confidence = "LOW"
            else:
                if dimension.confidence == "HIGH":
                    dimension.confidence = "MEDIUM"
            dimension.reasoning += note

    def _resolve_assets(
        self,
        assets: list[TradeAsset],
        league_id: str,
        roster_id: int,
        direction_label: str | None,
        target_roster_id: int | None = None,
    ) -> list[dict[str, Any]]:
        player_ids = self._extract_player_ids(assets)
        player_rows = {
            row["player_id"]: row
            for row in self._repo.get_player_values(player_ids, league_id, roster_id)
        }
        resolved: list[dict[str, Any]] = []
        for asset in assets:
            if asset.asset_type == "pick":
                resolved.append(
                    self._build_pick_proxy(
                        asset,
                        direction_label,
                        league_id=league_id,
                        target_roster_id=target_roster_id,
                    )
                )
                continue
            if asset.player_id is None:
                continue
            fallback = {
                "player_id": asset.player_id,
                "full_name": asset.player_id,
                "position": "UNKNOWN",
                "comp_insulation": 0.35,
                "comp_market_liquidity": 0.35,
                "comp_age_curve": 0.5,
                "comp_positional_scarcity": 0.35,
                "comp_short_term": 0.35,
                "lens_market": 0.35,
                "lens_insulation": 0.35,
                "lens_team_fit": 0.35,
                "lens_direction": 0.35,
                "lens_production": 0.35,
            }
            resolved.append(player_rows.get(asset.player_id, fallback))
        return resolved

    def _adjusted_package_value(self, values: list[dict[str, Any]], *, context: bool) -> float:
        value_fn = _asset_context_value if context else _asset_market_value
        sorted_values = sorted((value_fn(value) for value in values), reverse=True)
        adjusted = 0.0
        for index, market_value in enumerate(sorted_values):
            if index == 0:
                weight = 1.0
            elif index == 1:
                weight = 0.7
            elif index == 2:
                weight = 0.45
            else:
                weight = 0.2
            adjusted += market_value * weight
        return adjusted

    def _trade_balance(
        self,
        sending_values: list[dict[str, Any]],
        receiving_values: list[dict[str, Any]],
    ) -> TradeBalance:
        sent_raw = sum(_asset_market_value(value) for value in sending_values)
        received_raw = sum(_asset_market_value(value) for value in receiving_values)
        sent_market_adjusted = self._adjusted_package_value(sending_values, context=False)
        received_market_adjusted = self._adjusted_package_value(receiving_values, context=False)
        sent_adjusted = self._adjusted_package_value(sending_values, context=True)
        received_adjusted = self._adjusted_package_value(receiving_values, context=True)
        baseline = max(sent_adjusted, received_adjusted, 0.01)
        delta = received_adjusted - sent_adjusted
        raw_total = sent_raw + received_raw
        discounted_total = (sent_raw - sent_market_adjusted) + (
            received_raw - received_market_adjusted
        )
        context_gap = abs(
            (received_adjusted - sent_adjusted)
            - (received_market_adjusted - sent_market_adjusted)
        )
        notes: list[str] = []
        if raw_total > 0 and discounted_total / raw_total >= 0.08:
            notes.append(
                "Package concentration discounts lower-value add-ons instead of treating bench bulk as elite value."
            )
        if context_gap >= 0.03:
            notes.append(
                "App context differs from consensus after team fit, direction, insulation, production, scarcity, and liquidity lenses."
            )
        if any(
            value.get("valuation_source") == "static_pick_fallback"
            for value in sending_values + receiving_values
        ):
            notes.append(
                "static pick fallback was used for at least one pick because full pick valuation was unavailable."
            )
        if not notes:
            notes.append(
                "App context is close to consensus because the package is concentrated and the local lenses agree with market."
            )
        return TradeBalance(
            sent_raw_value=round(sent_raw, 4),
            received_raw_value=round(received_raw, 4),
            sent_adjusted_value=round(sent_adjusted, 4),
            received_adjusted_value=round(received_adjusted, 4),
            net_adjusted_delta=round(delta, 4),
            fairness_score=_clamp_score(50.0 + (delta / baseline) * 50.0),
            package_quality_note=" ".join(notes),
        )

    def _score_market_fairness(self, balance: TradeBalance) -> DimensionScore:
        baseline = max(balance.sent_adjusted_value, balance.received_adjusted_value, 0.01)
        delta = balance.net_adjusted_delta
        score = _clamp_score(50.0 + (delta / baseline) * 50.0)
        direction = "more" if delta > 0 else "less" if delta < 0 else "the same"
        reasoning = (
            f"You receive {abs(round((delta / baseline) * 100, 1))}% {direction} app-adjusted value than you send. "
            f"{balance.package_quality_note}"
            if delta != 0
            else f"Both sides are roughly even on app-adjusted value. {balance.package_quality_note}"
        )
        return DimensionScore(score=score, confidence="HIGH", reasoning=reasoning)

    def _score_roster_fit(
        self,
        sending_values: list[dict[str, Any]],
        receiving_values: list[dict[str, Any]],
        request: TradeRequest,
    ) -> DimensionScore:
        context = PositionalContext(self._conn, request.league_id, request.user_roster_id)
        sent_scores: list[float] = []
        received_scores: list[float] = []
        notes: list[str] = []
        for value in sending_values:
            score, value_notes = context.trade_send_cost(value)
            sent_scores.append(score)
            notes.extend(value_notes)
        for value in receiving_values:
            score, value_notes = context.trade_receive_value(value)
            received_scores.append(score)
            notes.extend(value_notes)
        delta = (sum(received_scores) / max(len(received_scores), 1)) - (
            sum(sent_scores) / max(len(sent_scores), 1)
        )
        score = _clamp_score(50.0 + delta * 50.0)
        descriptor = "high" if score >= 60 else "moderate" if score >= 45 else "low"
        note_text = f" ({'; '.join(dict.fromkeys(notes))})" if notes else ""
        return DimensionScore(
            score=score,
            confidence="MEDIUM",
            reasoning=f"Received assets have {descriptor} team fit relative to what you move out.{note_text}",
        )

    def _score_direction_fit(
        self,
        sending_values: list[dict[str, Any]],
        receiving_values: list[dict[str, Any]],
        direction: dict[str, Any] | None,
    ) -> DimensionScore:
        if direction is None:
            return DimensionScore(
                score=50.0,
                confidence="LOW",
                reasoning="No direction label available for this roster.",
            )
        sent = sum(float(value.get("lens_direction") or 0.0) for value in sending_values)
        received = sum(float(value.get("lens_direction") or 0.0) for value in receiving_values)
        baseline = max(sent, received, 0.01)
        score = _clamp_score(50.0 + ((received - sent) / baseline) * 50.0)
        label = str(direction["primary_label"]).replace("_", " ")
        if score > 55:
            reasoning = f"This trade advances your {label} direction."
        elif score < 45:
            reasoning = f"This trade conflicts with your {label} direction."
        else:
            reasoning = f"This trade has limited directional impact on your {label} plan."
        confidence = (
            "HIGH" if float(direction.get("confidence", 0.0)) >= 0.7 else "MEDIUM"
            if float(direction.get("confidence", 0.0)) >= 0.4
            else "LOW"
        )
        return DimensionScore(score=score, confidence=confidence, reasoning=reasoning)

    def _score_timing_quality(
        self, sending_values: list[dict[str, Any]], receiving_values: list[dict[str, Any]]
    ) -> DimensionScore:
        sent = [
            (float(value.get("comp_age_curve") or 0.0) + float(value.get("comp_short_term") or 0.0)) / 2.0
            for value in sending_values
        ]
        received = [
            (float(value.get("comp_age_curve") or 0.0) + float(value.get("comp_short_term") or 0.0)) / 2.0
            for value in receiving_values
        ]
        delta = (sum(received) / max(len(received), 1)) - (sum(sent) / max(len(sent), 1))
        score = _clamp_score(50.0 + delta * 50.0)
        wording = "gain" if score >= 50 else "lose"
        return DimensionScore(
            score=score,
            confidence="MEDIUM",
            reasoning=f"You {wording} age-curve and short-term timing leverage in this move.",
        )

    def _score_insulation_delta(
        self, sending_values: list[dict[str, Any]], receiving_values: list[dict[str, Any]]
    ) -> DimensionScore:
        sent = sum(
            (float(value.get("comp_insulation") or 0.0) + float(value.get("lens_insulation") or 0.0)) / 2.0
            for value in sending_values
        )
        received = sum(
            (float(value.get("comp_insulation") or 0.0) + float(value.get("lens_insulation") or 0.0)) / 2.0
            for value in receiving_values
        )
        baseline = max(sent, received, 0.01)
        score = _clamp_score(50.0 + ((received - sent) / baseline) * 50.0)
        return DimensionScore(
            score=score,
            confidence="MEDIUM",
            reasoning="Measures the net insulation you gain or lose across the swap.",
        )

    def _score_liquidity_delta(
        self, sending_values: list[dict[str, Any]], receiving_values: list[dict[str, Any]]
    ) -> DimensionScore:
        sent = sum(float(value.get("comp_market_liquidity") or 0.0) for value in sending_values)
        received = sum(float(value.get("comp_market_liquidity") or 0.0) for value in receiving_values)
        baseline = max(sent, received, 0.01)
        score = _clamp_score(50.0 + ((received - sent) / baseline) * 50.0)
        confidence = (
            "HIGH"
            if all(value.get("comp_market_liquidity") is not None for value in sending_values + receiving_values)
            else "MEDIUM"
        )
        direction = "more" if score >= 50 else "less"
        return DimensionScore(
            score=score,
            confidence=confidence,
            reasoning=f"Received assets are {direction} liquid than the assets you send out.",
        )

    def _score_manager_exploit(
        self,
        receiving_values: list[dict[str, Any]],
        manager_profile: dict[str, Any] | None,
        market_fairness: DimensionScore,
        direction_fit: DimensionScore,
    ) -> DimensionScore:
        if manager_profile is None:
            return DimensionScore(
                score=50.0,
                confidence="LOW",
                reasoning="No counterparty profile available.",
            )
        primary = manager_profile.get("exploitation_primary")
        base = float(manager_profile.get("exploitability_score", 50.0))
        score = 50.0
        if primary == "value_loss":
            score = 50.0 + max(0.0, market_fairness.score - 50.0) * 1.1
        elif primary == "directional_incoherence":
            score = 50.0 + max(0.0, direction_fit.score - 50.0) * 0.9
        elif primary == "archetype_overpay":
            qb_present = any(value.get("position") == "QB" for value in receiving_values)
            score = 68.0 if qb_present else 54.0
        else:
            score = 50.0 + max(0.0, base - 50.0) * 0.35
        confidence = (
            "LOW"
            if int(manager_profile.get("evidence_count", 0)) < 10
            else "MEDIUM"
        )
        label = str(primary or "manager tendencies").replace("_", " ")
        reasoning = f"This offer {'targets' if score >= 55 else 'does not strongly target'} {label} tendencies."
        return DimensionScore(score=_clamp_score(score), confidence=confidence, reasoning=reasoning)

    def _compute_strategic_distinction(
        self,
        market_fairness: DimensionScore,
        direction_fit: DimensionScore,
        direction_label: str,
    ) -> StrategicDistinction:
        label = direction_label.replace("_", " ")
        if market_fairness.score >= MARKET_FAIR_THRESHOLD and direction_fit.score > DIRECTION_ADVANCING_THRESHOLD:
            return StrategicDistinction(
                verdict="advancing",
                headline=f"Market fair and advances your {label}",
                explanation="The market price is acceptable and the assets align with your current roster direction.",
            )
        if market_fairness.score >= MARKET_FAIR_THRESHOLD and direction_fit.score < DIRECTION_NEGATIVE_THRESHOLD:
            return StrategicDistinction(
                verdict="negative",
                headline=f"Market fair but moves you away from your {label}",
                explanation="The price is defensible, but the incoming assets undercut the team path you are trying to follow.",
            )
        return StrategicDistinction(
            verdict="neutral",
            headline="Market fair with limited directional impact",
            explanation="The deal is roughly acceptable on price, but it does not materially change your team path.",
        )

    def evaluate(
        self,
        request: TradeRequest,
        *,
        include_recommendation_cards: bool = True,
    ) -> TradeEvaluation:
        self._degradation_reasons = []
        direction = self._repo.get_team_direction(request.league_id, request.user_roster_id)
        direction_label = direction["primary_label"] if direction is not None else "roster plan"
        sending_values = self._resolve_assets(
            request.user_sends,
            request.league_id,
            request.user_roster_id,
            direction_label,
            target_roster_id=request.counterparty_roster_id,
        )
        receiving_values = self._resolve_assets(
            request.user_receives,
            request.league_id,
            request.user_roster_id,
            direction_label,
            target_roster_id=request.user_roster_id,
        )
        trade_balance = self._trade_balance(sending_values, receiving_values)
        market_fairness = self._score_market_fairness(trade_balance)
        roster_fit = self._score_roster_fit(sending_values, receiving_values, request)
        direction_fit = self._score_direction_fit(sending_values, receiving_values, direction)
        timing_quality = self._score_timing_quality(sending_values, receiving_values)
        insulation_delta = self._score_insulation_delta(sending_values, receiving_values)
        liquidity_delta = self._score_liquidity_delta(sending_values, receiving_values)
        manager_profile = (
            self._repo.get_manager_profile(request.league_id, request.counterparty_roster_id)
            if request.counterparty_roster_id is not None
            else None
        )
        manager_exploit_quality = self._score_manager_exploit(
            receiving_values,
            manager_profile,
            market_fairness,
            direction_fit,
        )
        third_party_evaluations = self._score_third_party_trades(request)
        self._apply_multi_team_context(
            third_party_evaluations,
            [
                market_fairness,
                roster_fit,
                direction_fit,
                timing_quality,
                insulation_delta,
                liquidity_delta,
                manager_exploit_quality,
            ],
        )
        strategic_distinction = self._compute_strategic_distinction(
            market_fairness,
            direction_fit,
            direction_label,
        )
        if third_party_evaluations:
            strategic_distinction.explanation += (
                f" Includes {len(third_party_evaluations)} scored third-party leg(s); "
                "reroutes and package framing can explain each participant's path."
            )
        evaluation = TradeEvaluation(
            market_fairness=market_fairness,
            roster_fit=roster_fit,
            direction_fit=direction_fit,
            timing_quality=timing_quality,
            insulation_delta=insulation_delta,
            liquidity_delta=liquidity_delta,
            manager_exploit_quality=manager_exploit_quality,
            strategic_distinction=strategic_distinction,
            trade_balance=trade_balance,
            third_party_evaluations=third_party_evaluations or None,
            degradation_reasons=self._degradation_reasons,
        )
        if include_recommendation_cards:
            evaluation.recommendation_cards = self._card_engine.build_trade_card(
                evaluation,
                request.league_id,
                request.user_roster_id,
                sending_values=sending_values,
                receiving_values=receiving_values,
                direction_label=direction_label,
            )
        return evaluation
