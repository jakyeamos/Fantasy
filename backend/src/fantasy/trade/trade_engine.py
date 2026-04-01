from __future__ import annotations

from typing import Any

import duckdb

from fantasy.intelligence.constants import REBUILD_DIRECTION_LABELS
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
    TradeAsset,
    TradeEvaluation,
    TradeRequest,
)
from fantasy.trade.trade_repo import TradeRepo


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


class TradeEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = TradeRepo(conn)
        self._card_engine = RecommendationCardEngine(conn)

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
            except Exception:
                pass

        base = PICK_MARKET_VALUES.get(int(asset.pick_round or 4), 0.05)
        direction_bonus = 0.25 if direction_label in REBUILD_DIRECTION_LABELS else -0.10
        return {
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
        }

    def _apply_multi_team_context(
        self,
        request: TradeRequest,
        dimensions: list[DimensionScore],
    ) -> None:
        third_party_trades = request.third_party_trades or []
        if not third_party_trades:
            return

        leg_summaries: list[str] = []
        max_imbalance = 0.0
        for i, leg in enumerate(third_party_trades, start=1):
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
            pct = abs(net) / baseline * 100
            max_imbalance = max(max_imbalance, pct)
            direction = "gains" if net > 0 else "gives up" if net < 0 else "breaks even on"
            leg_summaries.append(
                f"Sidecar leg {i} (roster {leg.roster_id}) {direction} "
                f"{round(pct, 1)}% net market value."
            )

        sidecar_note = " ".join(leg_summaries)
        note = (
            f" Multi-team context: {len(third_party_trades)} sidecar leg(s) scored. "
            f"{sidecar_note} Scoring anchors to your net swap; sidecar fairness is informational."
        )
        for dimension in dimensions:
            if max_imbalance > 25:
                # Highly imbalanced sidecar — a participant may reject the deal
                if dimension.confidence == "HIGH":
                    dimension.confidence = "MEDIUM"
                elif dimension.confidence == "MEDIUM":
                    dimension.confidence = "LOW"
            else:
                # Roughly balanced sidecar — light touch
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

    def _score_market_fairness(
        self, sending_values: list[dict[str, Any]], receiving_values: list[dict[str, Any]]
    ) -> DimensionScore:
        sent = sum(float(value.get("lens_market") or 0.0) for value in sending_values)
        received = sum(float(value.get("lens_market") or 0.0) for value in receiving_values)
        baseline = max(sent, received, 0.01)
        delta = received - sent
        score = _clamp_score(50.0 + (delta / baseline) * 50.0)
        confidence = (
            "HIGH"
            if all(value.get("lens_market") is not None for value in sending_values + receiving_values)
            else "LOW"
        )
        direction = "more" if delta > 0 else "less" if delta < 0 else "the same"
        reasoning = (
            f"You receive {abs(round((delta / baseline) * 100, 1))}% {direction} market value than you send."
            if delta != 0
            else "Both sides are roughly even on market value."
        )
        return DimensionScore(score=score, confidence=confidence, reasoning=reasoning)

    def _score_roster_fit(
        self, sending_values: list[dict[str, Any]], receiving_values: list[dict[str, Any]]
    ) -> DimensionScore:
        sent = [
            (float(value.get("lens_team_fit") or 0.0) + float(value.get("comp_positional_scarcity") or 0.0)) / 2.0
            for value in sending_values
        ]
        received = [
            (float(value.get("lens_team_fit") or 0.0) + float(value.get("comp_positional_scarcity") or 0.0)) / 2.0
            for value in receiving_values
        ]
        delta = (sum(received) / max(len(received), 1)) - (sum(sent) / max(len(sent), 1))
        score = _clamp_score(50.0 + delta * 50.0)
        descriptor = "high" if score >= 60 else "moderate" if score >= 45 else "low"
        return DimensionScore(
            score=score,
            confidence="MEDIUM",
            reasoning=f"Received assets have {descriptor} team fit relative to what you move out.",
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

    def evaluate(self, request: TradeRequest) -> TradeEvaluation:
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
        market_fairness = self._score_market_fairness(sending_values, receiving_values)
        roster_fit = self._score_roster_fit(sending_values, receiving_values)
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
        self._apply_multi_team_context(
            request,
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
        evaluation = TradeEvaluation(
            market_fairness=market_fairness,
            roster_fit=roster_fit,
            direction_fit=direction_fit,
            timing_quality=timing_quality,
            insulation_delta=insulation_delta,
            liquidity_delta=liquidity_delta,
            manager_exploit_quality=manager_exploit_quality,
            strategic_distinction=self._compute_strategic_distinction(
                market_fairness,
                direction_fit,
                direction_label,
            ),
        )
        evaluation.recommendation_cards = self._card_engine.build_trade_card(
            evaluation,
            request.league_id,
            request.user_roster_id,
            sending_values=sending_values,
            receiving_values=receiving_values,
            direction_label=direction_label,
        )
        return evaluation
