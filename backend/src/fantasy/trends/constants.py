from __future__ import annotations

COMPONENT_COLS: list[str] = [
    "comp_current_production",
    "comp_short_term",
    "comp_role_stability",
    "comp_age_curve",
    "comp_insulation",
    "comp_market_liquidity",
    "comp_positional_scarcity",
    "comp_fragility",
    "comp_ceiling",
    "comp_floor",
    "comp_rerollability",
    "comp_contract",
]

COMPONENT_WEIGHTS: dict[str, float] = {
    "comp_current_production": 0.14,
    "comp_short_term": 0.18,
    "comp_role_stability": 0.10,
    "comp_age_curve": 0.18,
    "comp_insulation": 0.08,
    "comp_market_liquidity": 0.06,
    "comp_positional_scarcity": 0.05,
    "comp_fragility": -0.10,
    "comp_ceiling": 0.05,
    "comp_floor": 0.03,
    "comp_rerollability": 0.02,
    "comp_contract": 0.01,
}

TREND_THRESHOLD: float = 0.07
OPPORTUNITY_GAP_THRESHOLD: float = 8.0

CONFIDENCE_MULTIPLIERS: dict[str, float] = {
    "HIGH": 1.0,
    "MEDIUM": 0.7,
    "LOW": 0.4,
}

CALENDAR_ESCALATION_LABELS: dict[str, str] = {
    "post_combine": "COMBINE WEEK - RANK ESCALATED",
    "post_nfl_draft": "POST-DRAFT WINDOW - RANK ESCALATED",
    "trade_deadline": "TRADE DEADLINE - RANK ESCALATED",
    "rookie_fever": "ROOKIE FEVER - RANK ESCALATED",
}

SIMILARITY_COMPONENTS: list[str] = [
    "comp_age_curve",
    "comp_ceiling",
    "comp_floor",
    "comp_role_stability",
    "comp_short_term",
]

ADP_TIER_BINS: list[tuple[int, int]] = [
    (1, 6),
    (7, 12),
    (13, 24),
    (25, 48),
    (49, 96),
    (97, 250),
]

GENERIC_FORMAT_ROW: tuple[float, bool, bool] = (0.5, False, False)
