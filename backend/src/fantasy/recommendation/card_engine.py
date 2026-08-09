from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
from pydantic import ValidationError

from fantasy.market.market_service import MarketService
from fantasy.player_flags.flag_repo import FlagRepo
from fantasy.recommendation.anti_overreaction import BEARISH_PRODUCTION_FLOOR, is_elite
from fantasy.recommendation.constants import confidence_label_from_score
from fantasy.recommendation.gap_engine import MarketGapEngine
from fantasy.recommendation.models import RecommendationCard, SupportingFactor
from fantasy.intelligence.models import PlayerValue
from fantasy.trends.models import TrendResult

if TYPE_CHECKING:
    from fantasy.lineup.models import HygieneSuggestion, LineupResult, LineupSlotScore
    from fantasy.trade.models import DimensionScore, TradeEvaluation
    from fantasy.waiver.models import WaiverRecommendation


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_priority(impact: float, confidence: float, execution: float, urgency: float) -> int:
    raw_score = _clamp01(impact) * _clamp01(confidence) * _clamp01(execution) * _clamp01(urgency)
    return max(1, min(100, round((1.0 - raw_score) * 99) + 1))


class RecommendationCardEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._gap_engine = MarketGapEngine()
        self._flag_repo = FlagRepo(conn)
        self._market_service = MarketService(conn)

    def _confidence_score(self, label: str) -> float:
        if label == "HIGH":
            return 0.85
        if label == "MEDIUM":
            return 0.65
        return 0.35

    def _magnitude_from_score(self, score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    def _factor_from_dimension(self, name: str, dimension: "DimensionScore") -> SupportingFactor:
        normalized = _clamp01(float(dimension.score) / 100.0)
        if normalized >= 0.55:
            direction = "positive"
        elif normalized <= 0.45:
            direction = "negative"
        else:
            direction = "neutral"
        return SupportingFactor(
            factor_name=name,
            direction=direction,
            magnitude=self._magnitude_from_score(normalized),
            explanation=dimension.reasoning,
        )

    def _factor_from_flag(self, flag: str) -> SupportingFactor:
        copy = {
            "injury_recovery": ("Availability", "negative", "Player availability is still worth checking."),
            "depth_chart_competition": (
                "Depth chart pressure",
                "negative",
                "Market leverage is capped while the role is contested.",
            ),
            "role_expansion": (
                "Role expansion",
                "positive",
                "Recent role movement points to more usable weekly volume.",
            ),
            "role_compression": (
                "Role compression",
                "negative",
                "Role compression lowers the immediate path to upside.",
            ),
            "team_change": (
                "Team context",
                "neutral",
                "A recent team change shifts market expectations and deployment risk.",
            ),
            "age_cliff_proximity": (
                "Age curve",
                "negative",
                "Age curve risk is part of the recommendation posture here.",
            ),
        }
        factor_name, direction, explanation = copy.get(
            flag,
            ("Context note", "neutral", flag.replace("_", " ")),
        )
        return SupportingFactor(
            factor_name=factor_name,
            direction=direction,
            magnitude="medium",
            explanation=explanation,
        )

    def _player_value_row(self, league_id: str, player_id: str) -> tuple | None:
        return self._conn.execute(
            """
            SELECT roster_id,
                   comp_current_production,
                   comp_age_curve,
                   comp_insulation,
                   comp_ceiling,
                   comp_floor,
                   lens_production,
                   lens_market,
                   trend_result_json
            FROM player_values
            WHERE league_id = ? AND player_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            [league_id, player_id],
        ).fetchone()

    def model_vs_market_gap(self, league_id: str, player_id: str):
        row = self._player_value_row(league_id, player_id)
        if row is None or row[6] is None or row[7] is None:
            return None
        value = PlayerValue(
            league_id=league_id,
            roster_id=int(row[0]),
            player_id=player_id,
            comp_current_production=float(row[1]) if row[1] is not None else None,
            comp_age_curve=float(row[2]) if row[2] is not None else None,
            comp_insulation=float(row[3]) if row[3] is not None else None,
            comp_ceiling=float(row[4]) if row[4] is not None else None,
            comp_floor=float(row[5]) if row[5] is not None else None,
            lens_production=float(row[6]),
            lens_market=float(row[7]),
        )
        active_flag_types = [flag.flag_type for flag in self._flag_repo.get_active_flags(player_id)]
        anti_overreaction_fired = (
            is_elite(value)
            and (value.comp_current_production or 0.0) <= BEARISH_PRODUCTION_FLOOR
            and "injury_recovery" not in active_flag_types
            and "role_compression" not in active_flag_types
        )
        total_row = self._conn.execute("SELECT COUNT(*) FROM market_values").fetchone()
        player_total_count = int(total_row[0]) if total_row and total_row[0] is not None else 0
        if player_total_count <= 0:
            total_row = self._conn.execute(
                "SELECT COUNT(*) FROM player_values WHERE league_id = ?",
                [league_id],
            ).fetchone()
            player_total_count = int(total_row[0]) if total_row and total_row[0] is not None else 0
        return self._gap_engine.compute_model_vs_market_gap(
            lens_production=float(value.lens_production or 0.0),
            lens_market=float(value.lens_market or 0.0),
            fantasycalc_rank=self._market_service.get_fantasycalc_rank(player_id),
            player_total_count=player_total_count,
            anti_overreaction_fired=anti_overreaction_fired,
        )

    def _trend_result_from_players(self, league_id: str, player_ids: list[str]) -> TrendResult | None:
        for player_id in player_ids:
            row = self._player_value_row(league_id, player_id)
            if row is None or row[8] is None:
                continue
            try:
                return TrendResult.model_validate_json(row[8])
            except ValidationError:
                continue
        return None

    def _first_gap_from_players(self, league_id: str, player_ids: list[str]):
        for player_id in player_ids:
            gap = self.model_vs_market_gap(league_id, player_id)
            if gap is not None:
                return gap
        return None

    def build_trade_card(
        self,
        evaluation: "TradeEvaluation",
        league_id: str,
        user_roster_id: int,
        *,
        sending_values: list[dict] | None = None,
        receiving_values: list[dict] | None = None,
        direction_label: str | None = None,
    ) -> list[RecommendationCard]:
        del user_roster_id
        sending_values = sending_values or []
        receiving_values = receiving_values or []
        confidence_score = sum(
            [
                self._confidence_score(evaluation.market_fairness.confidence),
                self._confidence_score(evaluation.roster_fit.confidence),
                self._confidence_score(evaluation.direction_fit.confidence),
                self._confidence_score(evaluation.timing_quality.confidence),
            ]
        ) / 4.0
        impact = max(
            float(evaluation.market_fairness.score) / 100.0,
            float(evaluation.direction_fit.score) / 100.0,
        )
        urgency = float(evaluation.timing_quality.score) / 100.0
        execution = 0.75 if float(evaluation.manager_exploit_quality.score) >= 50 else 0.6
        distinction = evaluation.strategic_distinction
        direction_copy = direction_label.replace("_", " ") if direction_label else "current plan"
        if (
            evaluation.direction_fit.confidence == "LOW"
            and "first in both win-now and future value" in evaluation.direction_fit.reasoning
        ):
            action = (
                "Counter for a lineup-improving asset; keep the favorable value package as the fallback."
                if float(evaluation.market_fairness.score) >= 55
                else "Require a clear lineup upgrade before moving an elite cornerstone."
            )
        elif float(evaluation.direction_fit.score) >= 55 and float(evaluation.market_fairness.score) >= 50:
            action = "Push this trade forward or counter around the same structure."
        elif float(evaluation.direction_fit.score) <= 45:
            action = "Rework the deal before sending it, or walk away."
        else:
            action = "Keep the framework in play, but tighten the price."
        candidate_ids = [
            str(value["player_id"])
            for value in receiving_values + sending_values
            if value.get("player_id")
        ]
        card = RecommendationCard(
            recommendation_type="trade",
            priority_rank=compute_priority(impact, confidence_score, execution, urgency),
            headline=distinction.headline,
            action=action,
            target_entity_type="player" if candidate_ids else "manager",
            target_entity_ids=candidate_ids or [direction_copy],
            why_summary=distinction.explanation,
            supporting_factors=[
                self._factor_from_dimension("Market Fairness", evaluation.market_fairness),
                self._factor_from_dimension("Direction Fit", evaluation.direction_fit),
                self._factor_from_dimension("Roster Fit", evaluation.roster_fit),
                self._factor_from_dimension("Timing Quality", evaluation.timing_quality),
            ],
            confidence_label=confidence_label_from_score(confidence_score),
            confidence_score=confidence_score,
            downside_of_inaction="Waiting can narrow the timing edge or let the counterparty find a better path.",
            what_would_change_this_call=(
                "A materially different price, a shift in your team direction, or fresher market movement "
                "around the main assets."
            ),
            horizon="30_days",
            league_specificity_notes="Trade pricing is grounded in this league's existing value environment.",
            manager_specificity_notes=evaluation.manager_exploit_quality.reasoning,
            model_vs_market_gap=self._first_gap_from_players(league_id, candidate_ids),
            trend_result=self._trend_result_from_players(league_id, candidate_ids),
            cta_label="Evaluate This Trade",
            cta_destination=f"/trades?leagueId={league_id}",
        )
        return [card]

    def build_lineup_cards(self, result: "LineupResult") -> list[RecommendationCard]:
        if not result.slot_scores:
            return []
        ordered_slots = sorted(
            result.slot_scores,
            key=lambda slot: (
                slot.upgrade_leverage_score * slot.format_urgency_weight,
                slot.upgrade_leverage_score,
            ),
            reverse=True,
        )
        best_slot = ordered_slots[0]
        leverage = _clamp01(best_slot.upgrade_leverage_score)
        confidence_score = _clamp01(0.45 + (float(result.title_window_composite) * 0.45))
        if leverage > 0:
            headline = f"Upgrade {best_slot.position} to raise weekly ceiling"
            action = f"Shop for a stronger {best_slot.position} starter or a more insulated weekly option."
            recommendation_type = "trade"
        else:
            headline = f"Protect the {result.title_window_label.lower()} lineup shape"
            action = "Keep the starting core stable unless the market overpays for a bench piece."
            recommendation_type = "hold"
        supporting_factors = [
            SupportingFactor(
                factor_name="Title window",
                direction=(
                    "positive"
                    if result.title_window_label == "Peak Window"
                    else "negative"
                    if result.title_window_label == "Outside Window"
                    else "neutral"
                ),
                magnitude=self._magnitude_from_score(float(result.title_window_composite)),
                explanation=(
                    f"Current title-window label is {result.title_window_label} with "
                    f"{result.title_window_composite:.2f} composite strength."
                ),
            ),
            SupportingFactor(
                factor_name="Upgrade leverage",
                direction="positive" if leverage > 0 else "neutral",
                magnitude=self._magnitude_from_score(leverage),
                explanation=(
                    f"{best_slot.player_name} is the clearest leverage point against the contender benchmark."
                    if leverage > 0
                    else "No individual slot is far enough behind the field to force immediate action."
                ),
            ),
        ]
        supporting_factors.extend(
            self._factor_from_flag(flag) for flag in best_slot.player_context_flags[:2]
        )
        return [
            RecommendationCard(
                recommendation_type=recommendation_type,
                priority_rank=compute_priority(
                    max(leverage, float(result.upgrade_title_equity_delta)),
                    confidence_score,
                    0.65,
                    max(0.35, leverage * max(best_slot.format_urgency_weight, 1.0)),
                ),
                headline=headline,
                action=action,
                target_entity_type="position",
                target_entity_ids=[best_slot.position],
                why_summary=(
                    f"{best_slot.player_name} at {best_slot.position} is the cleanest leverage point "
                    "from the current lineup build."
                ),
                supporting_factors=supporting_factors,
                confidence_label=confidence_label_from_score(confidence_score),
                confidence_score=confidence_score,
                downside_of_inaction="Leaving the weakest starter slot untouched keeps weekly equity on the table.",
                what_would_change_this_call="A healthier bench option, a role change, or a different title-window read.",
                horizon="this_week",
                league_specificity_notes="Contender benchmarks are derived from this league's active starters.",
                manager_specificity_notes=None,
                model_vs_market_gap=self.model_vs_market_gap(result.league_id, best_slot.player_id),
                trend_result=self._trend_result_from_players(result.league_id, [best_slot.player_id]),
                cta_label="Open Overview",
                cta_destination=f"/league/{result.league_id}",
            )
        ]

    def build_hygiene_card(self, suggestion: "HygieneSuggestion", league_id: str) -> RecommendationCard:
        recommendation_type = {
            "consolidate": "trade",
            "cut": "drop",
            "stash": "stash",
            "taxi": "taxi",
            "hold": "hold",
            "shop": "shop",
            "package": "package",
            "handcuff_speculative": "stash",
            "reroll_into_pick": "reroll",
            "throw_in_now": "package",
        }.get(suggestion.action_type, "hold")
        confidence_score = _clamp01(0.45 + (float(suggestion.direction_fit_score) * 0.4))
        supporting_factors = [
            SupportingFactor(
                factor_name="Direction fit",
                direction="positive" if suggestion.direction_fit_score >= 0.55 else "negative",
                magnitude=self._magnitude_from_score(float(suggestion.direction_fit_score)),
                explanation=suggestion.timing_rationale,
            )
        ]
        supporting_factors.extend(
            self._factor_from_flag(flag) for flag in suggestion.player_context_flags[:2]
        )
        target_ids = [str(player_id) for player_id in suggestion.primary_player_ids]
        return RecommendationCard(
            recommendation_type=recommendation_type,
            priority_rank=compute_priority(
                float(suggestion.direction_fit_score),
                confidence_score,
                0.75,
                0.6,
            ),
            headline=f"{suggestion.action_type.replace('_', ' ').title()}: {', '.join(suggestion.primary_player_names[:2])}",
            action=suggestion.reasoning,
            target_entity_type="player",
            target_entity_ids=target_ids,
            why_summary=suggestion.reasoning,
            supporting_factors=supporting_factors,
            confidence_label=confidence_label_from_score(confidence_score),
            confidence_score=confidence_score,
            downside_of_inaction="Letting the roster edge sit can turn a flexible asset into dead weight.",
            what_would_change_this_call="A role shift, a fresh injury update, or a stronger trade counter.",
            horizon="30_days",
            league_specificity_notes="This recommendation is tuned to your current roster construction and league supply.",
            manager_specificity_notes=(
                f"Target manager: {suggestion.counterparty_name}"
                if suggestion.counterparty_name
                else None
            ),
            model_vs_market_gap=suggestion.model_vs_market_gap
            or self._first_gap_from_players(league_id, target_ids),
            trend_result=self._trend_result_from_players(league_id, target_ids),
            cta_label="Review Roster",
            cta_destination=f"/league/{league_id}",
        )

    def build_hygiene_cards(
        self,
        suggestions: list["HygieneSuggestion"],
        league_id: str,
    ) -> list[RecommendationCard]:
        return [self.build_hygiene_card(suggestion, league_id) for suggestion in suggestions[:5]]

    def build_waiver_card(self, rec: "WaiverRecommendation", league_id: str) -> RecommendationCard:
        urgency_score = {"High": 0.9, "Medium": 0.6, "Low": 0.3}.get(rec.urgency, 0.5)
        confidence_score = 0.7 if rec.is_immediate_start else 0.55
        return RecommendationCard(
            recommendation_type="bid" if rec.recommendation_label == "faab_bid" else "stash",
            priority_rank=compute_priority(0.7, confidence_score, 0.85, urgency_score),
            headline=f"Add {rec.player_name} ({rec.position})",
            action=rec.rationale,
            target_entity_type="player",
            target_entity_ids=[rec.player_id],
            why_summary=rec.rationale,
            supporting_factors=[
                SupportingFactor(
                    factor_name="Urgency",
                    direction="positive" if rec.urgency == "High" else "neutral",
                    magnitude="high" if rec.urgency == "High" else "medium",
                    explanation=f"Current waiver urgency is {rec.urgency}.",
                )
            ],
            confidence_label=confidence_label_from_score(confidence_score),
            confidence_score=confidence_score,
            downside_of_inaction="If this player clears waivers, replacement paths get thinner.",
            what_would_change_this_call="A better free-agent option or a change in roster need.",
            horizon="this_week",
            league_specificity_notes="Waiver priority is derived from this league's roster needs and FAAB state.",
            manager_specificity_notes=None,
            model_vs_market_gap=None,
            cta_label="Check Waivers",
            cta_destination=f"/league/{league_id}/waivers",
        )

    def build_waiver_cards(
        self,
        recommendations: list["WaiverRecommendation"],
        league_id: str,
    ) -> list[RecommendationCard]:
        return [self.build_waiver_card(rec, league_id) for rec in recommendations[:3]]


__all__ = ["RecommendationCardEngine", "compute_priority"]
