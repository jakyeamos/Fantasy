"""All Phase 6 pick valuation constants. No magic numbers in engine code."""

from __future__ import annotations

# --- Slot-to-value curve ---
SLOT_VALUE_DECAY_EXPONENT: float = 0.6       # power decay k in value = base * (1/slot)^k
FIRST_ROUND_BASE_VALUE: float = 100.0        # normalized base for 1.01

# --- Calendar timing multipliers (month: multiplier) ---
CALENDAR_TIMING_MULTIPLIERS: dict[int, float] = {
    1: 1.05,   # January — post-season, rising
    2: 1.10,   # February — draft speculation heating up
    3: 1.12,   # March — NFL free agency, class clarifying
    4: 1.18,   # April — NFL Draft week, peak rookie fever
    5: 1.08,   # May — fantasy rookie draft, still elevated
    6: 0.95,   # June — hype deflating
    7: 0.88,   # July — training camp, future uncertainty
    8: 0.87,   # August — preseason, picks discounted for immediate needs
    9: 0.85,   # September — season starts, picks cheapest
    10: 0.87,  # October — mid-season, slight uptick
    11: 0.92,  # November — trade deadline, rebuilders engaged
    12: 0.98,  # December — playoff push trades, picks moving
}
NEAR_PEAK_MONTHS: frozenset[int] = frozenset({2, 3, 4})

# --- Class strength hook (Phase 7 injects non-zero value) ---
CLASS_STRENGTH_WEIGHT: float = 0.20  # max ±20% adjustment from class quality

# --- Rebuilder demand ---
NEUTRAL_REBUILDER_RATIO: float = 0.25    # ~3 of 12 — baseline expectation
MAX_REBUILDER_PREMIUM: float = 0.15      # maximum ±15% adjustment from rebuilder count

# --- Per-manager demand factor ---
DIRECTION_DEMAND_WEIGHT: float = 0.6     # direction label weighted more than history
HISTORY_DEMAND_WEIGHT: float = 0.4
DEMAND_HISTORY_SIGMOID_K: float = 8.0
DEMAND_HISTORY_SIGMOID_CENTER: float = 0.40   # 40% pick reception rate = neutral
DEMAND_FACTOR_MAX_PREMIUM: float = 0.10       # max ±10% adjustment from per-manager demand
MIN_TRADE_EVIDENCE_THRESHOLD: int = 10         # from Phase 4 — same constant reused (D-09)

# --- Timing recommendation thresholds ---
EARLY_PICK_SLOT_THRESHOLD: int = 4       # slot ≤ 4 = "early first round" for timing logic
TRENDING_WINDOW: int = 4                 # look at last N games for trend detection
TRENDING_DOWN_THRESHOLD: float = 0.25   # fewer than 1 win in last 4 games = trending down
SEASON_MIDPOINT_THRESHOLD: int = 5      # at least 5 games remaining to trigger mid-season sell

# --- Multi-year pick discount ---
FUTURE_YEAR_DISCOUNT_RATE: float = 0.80  # 80% per year out from current (Pitfall 2)

# --- Season length ---
TOTAL_SEASON_GAMES: int = 14             # standard dynasty regular season

# --- Direction label -> demand score mapping ---
DIRECTION_DEMAND_MAP: dict[str, float] = {
    "hard_rebuild": 1.0,
    "elite_value_accumulation": 0.9,
    "one_year_punt": 0.8,
    "retool": 0.6,
    "productive_struggle": 0.5,
    "fringe_playoff": 0.4,
    "fragile_contender": 0.2,
    "true_contender": 0.1,
}

# --- Timing reasoning templates ---
TIMING_REASONING_TEMPLATES: dict[str, str] = {
    "sell_now_peak_window": "Near peak rookie fever window (Apr) — sell before the draft inflates competition",
    "sell_now_trending_down": "Team trending down ({recent_wins} wins last {window} games) — sell before slot worsens",
    "hold_rookie_fever": "Calendar at buy window (Sep–Jan) — hold until April rookie fever to maximize return",
    "use_on_the_clock": "Draft in progress — use or trade immediately",
}
