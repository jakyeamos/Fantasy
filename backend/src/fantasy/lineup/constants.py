from __future__ import annotations

from typing import Literal

TITLE_WINDOW_LABELS = Literal["Peak Window", "Fading Window", "Outside Window"]

TITLE_WINDOW_WEIGHTS = {
    "ceiling": 0.60,
    "stability": 0.25,
    "depth": 0.15,
}

PEAK_WINDOW_THRESHOLD = 0.65
FADING_WINDOW_THRESHOLD = 0.35

TITLE_WINDOW_FRAGILITY_BOOST = 0.15

HYGIENE_MAX_SUGGESTIONS_PER_TYPE = 5

HYGIENE_ACTION_TYPES = Literal[
    "consolidate",
    "cut",
    "stash",
    "taxi",
    "hold",
    "shop",
    "package",
    "handcuff_speculative",
    "reroll_into_pick",
    "throw_in_now",
]

ELITE_INSULATION_THRESHOLD = 0.65
CONTENDER_TIER_FRACTION = 0.33
TE_NON_PREMIUM_URGENCY_WEIGHT = 0.6
UPGRADE_LEVERAGE_BASE_EQUITY = 0.08
AGE_CLIFF_PROXIMITY_SEASONS = 2

CUT_VALUE_FLOOR = 0.10

STASH_AGE_CEILING = 24
STASH_CEILING_FLOOR = 0.30
