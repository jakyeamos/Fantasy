from __future__ import annotations

DIMENSION_WEIGHTS = {
    "market_fairness": 1.0,
    "roster_fit": 1.0,
    "direction_fit": 1.0,
    "timing_quality": 0.8,
    "insulation_delta": 0.7,
    "liquidity_delta": 0.7,
    "manager_exploit_quality": 0.6,
}

MARKET_FAIR_THRESHOLD = 40
DIRECTION_NEGATIVE_THRESHOLD = 45
DIRECTION_ADVANCING_THRESHOLD = 55
MAX_REROUTES = 3
MIN_EXPLOIT_EVIDENCE_THRESHOLD = 10
PLAYER_SEARCH_LIMIT = 20

PICK_MARKET_VALUES = {
    1: 0.70,
    2: 0.45,
    3: 0.25,
    4: 0.10,
}

DIMENSION_CONFIDENCE_RULES = {
    "market_fairness": "HIGH when both sides have market values, LOW otherwise",
    "roster_fit": "MEDIUM unless all assets have team-fit data",
    "direction_fit": "HIGH when direction confidence >= 0.7, LOW when unavailable",
    "timing_quality": "MEDIUM",
    "insulation_delta": "MEDIUM",
    "liquidity_delta": "HIGH when all assets have liquidity values, MEDIUM otherwise",
    "manager_exploit_quality": "LOW below evidence threshold, MEDIUM otherwise",
}
