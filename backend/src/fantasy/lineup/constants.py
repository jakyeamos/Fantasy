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

HYGIENE_ACTION_TYPES = Literal["consolidate", "cut", "stash", "taxi"]

CUT_VALUE_FLOOR = 0.10

STASH_AGE_CEILING = 24
STASH_CEILING_FLOOR = 0.30
