from __future__ import annotations

GAP_THRESHOLD: float = 8.0
MAX_TIER_COUNT: int = 5

TIER_LABELS: dict[int, str] = {
    1: "Tier 1 - Elite",
    2: "Tier 2 - Strong Day 2",
    3: "Tier 3 - Day 3 Upside",
    4: "Tier 4 - Developmental",
    5: "Tier 5 - Flier",
}

RISK_BAND_LOW = "Low"
RISK_BAND_MODERATE = "Moderate"
RISK_BAND_HIGH = "High"

ARCHETYPE_LABELS: dict[str, list[str]] = {
    "WR": [
        "Deep Threat",
        "Slot Receiver",
        "Contested Catch WR",
        "Route Runner",
        "Possession WR",
    ],
    "RB": [
        "Workhorse",
        "Early Down Back",
        "Third Down Back",
        "Receiving Back",
        "Power Back",
    ],
    "QB": [
        "Pocket Passer",
        "Dual Threat QB",
        "Scrambler",
        "Pro Style QB",
    ],
    "TE": [
        "Inline Blocker",
        "Move TE",
        "Receiving TE",
        "H-Back",
    ],
}
ARCHETYPE_FALLBACK_TEMPLATE = "{position} Prospect"

BASELINE_TIER1_COUNT: int = 3
BASELINE_TIER2_COUNT: int = 5
CLASS_TIER1_WEIGHT: float = 0.70
CLASS_TIER2_WEIGHT: float = 0.30

SLOT_AVAILABILITY_SLOPE: float = 0.08
SLOT_AVAILABILITY_MAX_SLOT_MULTIPLIER: int = 2

TENDENCY_MIN_SAMPLE_SIZE: int = 3
POSITIONAL_RUN_THRESHOLD: float = 1.2
VALUE_GAP_THRESHOLD: float = 2.0

STRONG_TIER2_THRESHOLD: float = 65.0
CLASS_WEAKNESS_THRESHOLD: float = -0.2
EARLY_PICK_VALUE_THRESHOLD: int = 4
