from __future__ import annotations


CONFIDENCE_HIGH_THRESHOLD: float = 0.75
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50


def confidence_label_from_score(score: float) -> str:
    if score >= CONFIDENCE_HIGH_THRESHOLD:
        return "HIGH"
    if score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


__all__ = [
    "CONFIDENCE_HIGH_THRESHOLD",
    "CONFIDENCE_MEDIUM_THRESHOLD",
    "confidence_label_from_score",
]
