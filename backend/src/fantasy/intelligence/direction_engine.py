from __future__ import annotations

import math

from fantasy.intelligence.constants import (
    DIRECTION_MOVE_MATRIX,
    DIRECTION_WEIGHTS,
    MOVE_TYPE_TARGETS,
    VALID_DIRECTION_LABELS,
)
from fantasy.intelligence.models import DirectionResult, TeamScorecard


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


_CONFIDENCE_SOFTMAX_TEMPERATURE = 0.032
_LOW_CONFIDENCE_THRESHOLD = 0.4


class DirectionEngine:
    _LABEL_CONTEXT = {
        "true_contender": "True contender teams have high win-now production with depth to protect the ceiling.",
        "fragile_contender": "Fragile contender teams can win now, but their path is narrow and exposed to volatility.",
        "fringe_playoff": "Fringe playoff teams are competitive enough to matter, but not insulated enough to force an all-in push.",
        "transition_contender": "Transition contender teams still have a real weekly ceiling, but they need to preserve future flexibility instead of forcing a premature shove.",
        "productive_struggle": "Productive struggle teams can score now while still redirecting value toward the future.",
        "one_year_punt": "One-year punt teams intentionally defer points to maximize future leverage.",
        "retool": "Retool teams keep a workable core while actively stripping out age and fragility.",
        "value_retool": "Value retool teams keep enough of a scoring spine to stay alive while leaning harder into optionality, liquidity, and patient value collection.",
        "elite_value_accumulation": "Elite value accumulation teams prioritize liquid value and optionality over immediate lineup points.",
        "soft_rebuild": "Soft rebuild teams are future-first, but they still carry enough usable production that a total tear-down is not the cleanest description.",
        "hard_rebuild": "Hard rebuild teams sacrifice current points to maximize youth and pick capital.",
    }

    def classify(self, scorecard: TeamScorecard) -> DirectionResult:
        scores = scorecard.as_dict()
        label_scores = self._compute_label_scores(scores)
        ranked = sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
        primary_label, primary_score = ranked[0]
        confidence = self._compute_confidence(label_scores)
        alternates = self._compute_alternates(ranked, primary_score)
        delta = self._compute_delta(scores, ranked)
        reasoning = self._build_reasoning(primary_label, scores, primary_score)
        if confidence < _LOW_CONFIDENCE_THRESHOLD:
            reasoning = f"Low confidence — {reasoning}"
        return DirectionResult(
            primary_label=primary_label,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            alternates=alternates,
            delta=delta,
            approved_moves=self.rank_moves(primary_label, scorecard),
            discouraged_moves=DIRECTION_MOVE_MATRIX[primary_label]["discouraged"],
        )

    def rank_moves(self, direction_label: str, scorecard: TeamScorecard) -> list[str]:
        approved = DIRECTION_MOVE_MATRIX[direction_label]["approved"]
        scores = scorecard.as_dict()
        return sorted(
            approved,
            key=lambda move: scores.get(MOVE_TYPE_TARGETS.get(move, ""), 0.5),
        )

    def _compute_label_scores(self, scores: dict[str, float]) -> dict[str, float]:
        return {
            label: sum(scores[dimension] * weight for dimension, weight in weights.items())
            for label, weights in DIRECTION_WEIGHTS.items()
        }

    def _compute_confidence(self, label_scores: dict[str, float]) -> float:
        if len(label_scores) < 2:
            return 1.0

        sorted_scores = sorted(label_scores.values(), reverse=True)
        scaled_scores = [
            score / _CONFIDENCE_SOFTMAX_TEMPERATURE for score in sorted_scores
        ]
        max_scaled = max(scaled_scores)
        exp_scores = [math.exp(score - max_scaled) for score in scaled_scores]
        total = sum(exp_scores)
        if total < 1e-9:
            return 0.0

        top_probability = max(exp_score / total for exp_score in exp_scores)
        uniform_probability = 1.0 / len(sorted_scores)
        return _clamp01(
            (top_probability - uniform_probability)
            / max(1.0 - uniform_probability, 1e-9)
        )

    def _compute_alternates(
        self, ranked: list[tuple[str, float]], primary_score: float
    ) -> list[dict[str, float | str]]:
        threshold = primary_score * 0.85
        alternates = [
            {"label": label, "score": round(score, 3), "gap": round(primary_score - score, 3)}
            for label, score in ranked[1:]
            if score >= threshold
        ]
        for label, score in ranked[1:]:
            if len(alternates) >= 2:
                break
            if label not in {alternate["label"] for alternate in alternates}:
                alternates.append(
                    {"label": label, "score": round(score, 3), "gap": round(primary_score - score, 3)}
                )
        return alternates[: max(2, len(alternates))]

    def _compute_delta(
        self, scores: dict[str, float], ranked: list[tuple[str, float]]
    ) -> dict[str, float | str]:
        if len(ranked) < 2:
            return {"flip_to": ranked[0][0], "dimension": "win_now", "change_needed": 0.0, "direction": "increase"}
        primary_label, _ = ranked[0]
        secondary_label, _ = ranked[1]
        best_dimension = "win_now"
        best_change = 1.0
        best_direction = "increase"
        for dimension in scores:
            for direction in ("increase", "decrease"):
                changed_scores = dict(scores)
                for step in range(1, 21):
                    delta = 0.05 * step
                    changed_scores[dimension] = _clamp01(
                        scores[dimension] + (delta if direction == "increase" else -delta)
                    )
                    label_scores = self._compute_label_scores(changed_scores)
                    reranked = sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
                    if reranked[0][0] != primary_label:
                        if delta < best_change:
                            best_dimension = dimension
                            best_change = delta
                            best_direction = direction
                        break
        return {
            "flip_to": secondary_label,
            "dimension": best_dimension,
            "change_needed": round(best_change, 3),
            "direction": best_direction,
        }

    def _build_reasoning(self, label: str, scores: dict[str, float], label_score: float) -> str:
        weights = DIRECTION_WEIGHTS[label]
        ranked_dims = sorted(
            weights,
            key=lambda dimension: abs(scores[dimension] * weights[dimension]),
            reverse=True,
        )[:3]
        descriptors = []
        for dimension in ranked_dims:
            value = scores[dimension]
            if value >= 0.67:
                state = "high"
            elif value <= 0.33:
                state = "low"
            else:
                state = "mixed"
            descriptors.append(f"{dimension.replace('_', ' ')} is {state}")
        joined = ", ".join(descriptors[:2]) if len(descriptors) < 3 else ", ".join(descriptors[:2]) + f", and {descriptors[2]}"
        return f"Primary signal: {joined}. {self._LABEL_CONTEXT.get(label, label_score)}"


__all__ = ["DirectionEngine", "VALID_DIRECTION_LABELS"]
