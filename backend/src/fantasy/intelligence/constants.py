from __future__ import annotations

# Source: Phase 2 RESEARCH.md Pattern 2 / domain judgment for remaining labels.
DIRECTION_WEIGHTS: dict[str, dict[str, float]] = {
    "true_contender": {
        "win_now": 0.35,
        "future_value": 0.05,
        "depth": 0.20,
        "pick_capital": 0.05,
        "flexibility": 0.10,
        "fragility": -0.20,
        "age_risk": -0.05,
        "liquidity": 0.00,
        "positional_insulation": 0.10,
    },
    "fragile_contender": {
        "win_now": 0.30,
        "future_value": 0.00,
        "depth": 0.05,
        "pick_capital": 0.05,
        "flexibility": 0.10,
        "fragility": 0.20,
        "age_risk": -0.15,
        "liquidity": -0.05,
        "positional_insulation": 0.00,
    },
    "fringe_playoff": {
        "win_now": 0.22,
        "future_value": 0.08,
        "depth": 0.16,
        "pick_capital": 0.06,
        "flexibility": 0.12,
        "fragility": 0.06,
        "age_risk": -0.06,
        "liquidity": 0.08,
        "positional_insulation": 0.10,
    },
    "productive_struggle": {
        "win_now": 0.14,
        "future_value": 0.20,
        "depth": 0.08,
        "pick_capital": 0.10,
        "flexibility": 0.12,
        "fragility": 0.02,
        "age_risk": 0.04,
        "liquidity": 0.14,
        "positional_insulation": 0.08,
    },
    "one_year_punt": {
        "win_now": -0.10,
        "future_value": 0.26,
        "depth": 0.00,
        "pick_capital": 0.24,
        "flexibility": 0.10,
        "fragility": 0.04,
        "age_risk": 0.10,
        "liquidity": 0.10,
        "positional_insulation": 0.00,
    },
    "retool": {
        "win_now": 0.12,
        "future_value": 0.18,
        "depth": 0.08,
        "pick_capital": 0.08,
        "flexibility": 0.16,
        "fragility": -0.04,
        "age_risk": 0.14,
        "liquidity": 0.12,
        "positional_insulation": 0.08,
    },
    "elite_value_accumulation": {
        "win_now": -0.06,
        "future_value": 0.28,
        "depth": 0.04,
        "pick_capital": 0.18,
        "flexibility": 0.12,
        "fragility": 0.00,
        "age_risk": 0.06,
        "liquidity": 0.18,
        "positional_insulation": 0.02,
    },
    "hard_rebuild": {
        "win_now": -0.30,
        "future_value": 0.35,
        "depth": 0.10,
        "pick_capital": 0.25,
        "flexibility": 0.10,
        "fragility": 0.00,
        "age_risk": 0.10,
        "liquidity": 0.05,
        "positional_insulation": 0.00,
    },
}

# Source: Phase 2 RESEARCH.md Pattern 2 / domain-complete move matrix.
DIRECTION_MOVE_MATRIX: dict[str, dict[str, list[str]]] = {
    "true_contender": {
        "approved": ["sell_future_picks", "buy_aging_producers", "buy_depth", "waiver_streamers"],
        "discouraged": ["sell_proven_starters", "start_youth_at_position_of_need", "hoard_picks"],
    },
    "fragile_contender": {
        "approved": ["buy_depth", "buy_insulated_veterans", "sell_fragile_ceiling", "consolidate_for_starters"],
        "discouraged": ["empty_bench", "double_down_on_fragility", "hoard_long_term_assets"],
    },
    "fringe_playoff": {
        "approved": ["tier_down_for_depth", "buy_selective_help", "preserve_liquidity", "probe_market"],
        "discouraged": ["all_in_future_selloff", "hard_rebuild_dump", "lock_into_old_core"],
    },
    "productive_struggle": {
        "approved": ["sell_spike_weeks", "buy_young_starters", "accumulate_liquidity", "collect_future_seconds"],
        "discouraged": ["pay_peak_prices", "ignore_market_windows", "buy_fragile_veterans"],
    },
    "one_year_punt": {
        "approved": ["sell_aging_producers", "buy_rookie_picks", "bank_future_value", "defer_points"],
        "discouraged": ["buy_expiring_value", "short_term_patchwork", "empty_pick_drawer"],
    },
    "retool": {
        "approved": ["move_off_age_risk", "buy_underpriced_youth", "maintain_core_production", "rebalance_positions"],
        "discouraged": ["full_tank", "all_in_title_push", "bleed_liquidity"],
    },
    "elite_value_accumulation": {
        "approved": ["buy_mispriced_assets", "tier_down_for_extras", "hoard_picks", "store_liquidity"],
        "discouraged": ["force_lineup_points", "lock_into_old_vets", "sell_discounted_youth"],
    },
    "hard_rebuild": {
        "approved": ["sell_aging_producers", "buy_rookie_picks", "sell_win_now_pieces", "hoard_youth"],
        "discouraged": ["buy_expiring_value", "extend_aging_RBs", "win_now_trades"],
    },
}

CONTENDER_DIRECTION_LABELS = (
    "true_contender",
    "fragile_contender",
    "fringe_playoff",
)

REBUILD_DIRECTION_LABELS = (
    "productive_struggle",
    "one_year_punt",
    "elite_value_accumulation",
    "hard_rebuild",
)

# Source: Phase 2 RESEARCH.md Pattern 5 / ESPN age curve analysis 2023.
POSITIONAL_PEAK_AGE = {"RB": 26, "WR": 28, "TE": 30, "QB": 32}

# Source: Phase 2 RESEARCH.md Pattern 5 / ESPN age curve analysis 2023.
POSITIONAL_CLIFF_AGE = {"RB": 29, "WR": 31, "TE": 33, "QB": 35}

# Source: Phase 2 RESEARCH.md Code Examples.
ROUND_WEIGHTS = {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}

# Source: Phase 2 RESEARCH.md Pattern 4.
FORMAT_MULTIPLIERS = {
    "ppr_1.0": {"WR": 1.15, "TE": 1.10, "RB": 1.10, "QB": 1.0},
    "ppr_0.5": {"WR": 1.07, "TE": 1.05, "RB": 1.05, "QB": 1.0},
    "ppr_0.0": {"WR": 1.0, "TE": 1.0, "RB": 1.0, "QB": 1.0},
    "superflex": {"QB": 1.35},
    "tep": {"TE": 1.15},
}

_ALL_COMPONENTS = [
    "current_production",
    "short_term",
    "role_stability",
    "age_curve",
    "insulation",
    "market_liquidity",
    "positional_scarcity",
    "fragility",
    "ceiling",
    "floor",
    "rerollability",
    "contract",
]


def _weights(**kwargs: float) -> dict[str, float]:
    return {component: kwargs.get(component, 0.0) for component in _ALL_COMPONENTS}


# Source: Phase 2 RESEARCH.md Pattern 4 / label-specific extrapolation.
DIRECTION_VALUE_WEIGHTS: dict[str, dict[str, float]] = {
    "true_contender": _weights(
        current_production=0.30,
        short_term=0.20,
        role_stability=0.05,
        age_curve=-0.05,
        insulation=0.10,
        market_liquidity=0.05,
        positional_scarcity=0.05,
        fragility=-0.10,
        ceiling=0.15,
        floor=0.15,
        rerollability=-0.05,
        contract=0.05,
    ),
    "fragile_contender": _weights(
        current_production=0.24,
        short_term=0.18,
        role_stability=0.10,
        age_curve=-0.10,
        insulation=0.16,
        market_liquidity=0.05,
        positional_scarcity=0.04,
        fragility=-0.20,
        ceiling=0.10,
        floor=0.15,
        rerollability=-0.04,
        contract=0.02,
    ),
    "fringe_playoff": _weights(
        current_production=0.18,
        short_term=0.14,
        role_stability=0.10,
        age_curve=0.04,
        insulation=0.10,
        market_liquidity=0.10,
        positional_scarcity=0.08,
        fragility=-0.05,
        ceiling=0.10,
        floor=0.11,
        rerollability=0.04,
        contract=0.06,
    ),
    "productive_struggle": _weights(
        current_production=0.10,
        short_term=0.08,
        role_stability=0.08,
        age_curve=0.12,
        insulation=0.10,
        market_liquidity=0.12,
        positional_scarcity=0.06,
        fragility=-0.02,
        ceiling=0.14,
        floor=0.06,
        rerollability=0.08,
        contract=0.08,
    ),
    "one_year_punt": _weights(
        current_production=0.02,
        short_term=0.00,
        role_stability=0.05,
        age_curve=0.22,
        insulation=0.08,
        market_liquidity=0.14,
        positional_scarcity=0.05,
        fragility=0.00,
        ceiling=0.18,
        floor=-0.04,
        rerollability=0.12,
        contract=0.06,
    ),
    "retool": _weights(
        current_production=0.12,
        short_term=0.10,
        role_stability=0.10,
        age_curve=0.14,
        insulation=0.10,
        market_liquidity=0.12,
        positional_scarcity=0.06,
        fragility=-0.05,
        ceiling=0.10,
        floor=0.05,
        rerollability=0.08,
        contract=0.08,
    ),
    "elite_value_accumulation": _weights(
        current_production=0.04,
        short_term=0.02,
        role_stability=0.08,
        age_curve=0.18,
        insulation=0.10,
        market_liquidity=0.18,
        positional_scarcity=0.07,
        fragility=0.00,
        ceiling=0.12,
        floor=0.00,
        rerollability=0.13,
        contract=0.08,
    ),
    "hard_rebuild": _weights(
        current_production=0.05,
        short_term=0.00,
        role_stability=0.05,
        age_curve=0.30,
        insulation=0.10,
        market_liquidity=0.15,
        positional_scarcity=0.05,
        fragility=0.00,
        ceiling=0.25,
        floor=-0.05,
        rerollability=0.05,
        contract=0.00,
    ),
}

# Source: Phase 2 RESEARCH.md Pattern 6.
MOVE_TYPE_TARGETS: dict[str, str] = {
    "sell_aging_producers": "age_risk",
    "buy_rookie_picks": "pick_capital",
    "buy_depth": "depth",
    "sell_future_picks": "pick_capital",
    "buy_aging_producers": "win_now",
    "hoard_picks": "future_value",
    "sell_proven_starters": "liquidity",
    "waiver_streamers": "depth",
    "buy_insulated_veterans": "fragility",
    "sell_fragile_ceiling": "fragility",
    "consolidate_for_starters": "win_now",
    "tier_down_for_depth": "depth",
    "buy_selective_help": "win_now",
    "preserve_liquidity": "liquidity",
    "probe_market": "flexibility",
    "sell_spike_weeks": "liquidity",
    "buy_young_starters": "future_value",
    "accumulate_liquidity": "liquidity",
    "collect_future_seconds": "pick_capital",
    "bank_future_value": "future_value",
    "defer_points": "win_now",
    "move_off_age_risk": "age_risk",
    "buy_underpriced_youth": "future_value",
    "maintain_core_production": "win_now",
    "rebalance_positions": "flexibility",
    "buy_mispriced_assets": "liquidity",
    "tier_down_for_extras": "pick_capital",
    "store_liquidity": "liquidity",
    "sell_win_now_pieces": "win_now",
    "hoard_youth": "future_value",
}

VALID_DIRECTION_LABELS = tuple(DIRECTION_WEIGHTS.keys())
