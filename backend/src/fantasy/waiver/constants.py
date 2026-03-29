from __future__ import annotations

FREE_AGENT_VALUE_FLOOR: float = 15.0
FAAB_MAX_PCT_OF_REMAINING: float = 0.25
FAAB_SCARCITY_ADJ_MAX: float = 0.05
FAAB_URGENCY_ADJ_MAX: float = 0.05
FAAB_START_PENALTY: float = 0.03
FAAB_FLOOR_PCT: float = 0.01
FAAB_CEILING_PCT: float = 0.60
FAAB_LOW_MULT: float = 0.60
FAAB_HIGH_MULT: float = 1.40
STALE_INGEST_HOURS: int = 12

WAIVER_TYPE_LABELS: dict[int, str] = {
    0: "free_agent",
    1: "rolling",
    2: "faab",
}

DIRECTION_URGENCY: dict[str, float] = {
    "true_contender": 1.00,
    "fragile_contender": 0.90,
    "fringe_playoff": 0.75,
    "productive_struggle": 0.65,
    "retool": 0.55,
    "one_year_punt": 0.40,
    "elite_value_accumulation": 0.35,
    "hard_rebuild": 0.30,
}

BUILD_TEMPLATE_MAP: dict[str, str] = {
    "true_contender": "win_now",
    "fragile_contender": "win_now",
    "fringe_playoff": "balanced",
    "productive_struggle": "balanced",
    "one_year_punt": "rebuild",
    "retool": "balanced",
    "elite_value_accumulation": "rebuild",
    "hard_rebuild": "rebuild",
}

BUILD_TEMPLATE_HINTS: dict[str, str] = {
    "win_now": (
        "True Contender build: prioritize proven starters, trade picks for veterans, "
        "avoid late-round upside."
    ),
    "balanced": (
        "Balanced build: hold first-round picks, trade second-round picks for ascending "
        "24-27 year-old starters."
    ),
    "rebuild": (
        "Rebuild build: accumulate all picks, target 21-24 year-old upside, avoid "
        "win-now assets."
    ),
}

ORPHAN_WEIGHT_AGE_CURVE: float = 0.25
ORPHAN_WEIGHT_PICK_CAPITAL: float = 0.25
ORPHAN_WEIGHT_DEAD_SPOTS: float = 0.20
ORPHAN_WEIGHT_LINEUP: float = 0.20
ORPHAN_WEIGHT_LIQUIDATION: float = 0.10

ORPHAN_DISTRESSED_MAX: float = 30.0
ORPHAN_REBUILDER_MAX: float = 55.0
ORPHAN_BALANCED_MAX: float = 75.0

URGENCY_ORDER: dict[str, int] = {
    "this_week": 0,
    "30_days": 1,
    "offseason": 2,
}
