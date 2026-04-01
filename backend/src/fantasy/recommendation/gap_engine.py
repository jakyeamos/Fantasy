from __future__ import annotations

from fantasy.recommendation.models import ModelVsMarketGap


GAP_BUY_LOW_THRESHOLD: float = 0.20
GAP_LEAGUE_OPPORTUNITY_THRESHOLD: float = 0.10
GAP_ALIGNED_THRESHOLD: float = 0.10
GAP_IGNORE_DISCOUNT_THRESHOLD: float = 0.20


class MarketGapEngine:
    def classify(self, gap: float, anti_overreaction_fired: bool) -> str:
        if anti_overreaction_fired:
            return "hold_despite_weak_market"
        if gap > GAP_BUY_LOW_THRESHOLD:
            return "buy_low"
        if gap > GAP_LEAGUE_OPPORTUNITY_THRESHOLD:
            return "league_specific_opportunity"
        if gap >= -GAP_ALIGNED_THRESHOLD:
            return "market_right_model_cautious"
        if gap >= -GAP_IGNORE_DISCOUNT_THRESHOLD:
            return "ignore_false_discount"
        return "sell_high"

    def compute_model_vs_market_gap(
        self,
        lens_production: float,
        lens_market: float,
        fantasycalc_rank: int | None,
        player_total_count: int,
        anti_overreaction_fired: bool,
    ) -> ModelVsMarketGap:
        gap = lens_production - lens_market
        if gap > GAP_ALIGNED_THRESHOLD:
            direction = "model_above"
            direction_text = "higher"
        elif gap < -GAP_ALIGNED_THRESHOLD:
            direction = "model_below"
            direction_text = "lower"
        else:
            direction = "aligned"
            direction_text = "roughly aligned with"

        model_rank = (
            round((1.0 - lens_production) * max(player_total_count, 1))
            if player_total_count > 0
            else None
        )
        classification = self.classify(gap, anti_overreaction_fired)
        if classification == "hold_despite_weak_market":
            explanation = (
                "Model confidence stays stronger than the current market because the profile "
                "looks like short-term noise on an insulated asset."
            )
        else:
            explanation = (
                f"Model rates this asset {direction_text} the market by "
                f"{abs(gap):.2f} normalized points."
            )

        return ModelVsMarketGap(
            market_rank=fantasycalc_rank,
            model_rank=model_rank,
            market_value=lens_market,
            model_value=lens_production,
            gap_magnitude=abs(gap),
            gap_direction=direction,
            gap_classification=classification,
            explanation=explanation,
        )


__all__ = [
    "GAP_ALIGNED_THRESHOLD",
    "GAP_BUY_LOW_THRESHOLD",
    "GAP_IGNORE_DISCOUNT_THRESHOLD",
    "GAP_LEAGUE_OPPORTUNITY_THRESHOLD",
    "MarketGapEngine",
]
