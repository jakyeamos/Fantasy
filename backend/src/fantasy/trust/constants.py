from __future__ import annotations

from enum import StrEnum
from typing import Literal

RuleSupportLevel = Literal["supported", "partially_supported", "unsupported"]


class FormatRule(StrEnum):
    SUPERFLEX = "superflex"
    TEP = "tep"
    HALF_PPR = "half_ppr"
    FULL_PPR = "full_ppr"
    STANDARD = "standard"
    MEDIAN_WINS = "median_wins"
    BEST_BALL = "best_ball"
    IDP = "idp"
    SALARY_CAP = "salary_cap"
    DEVY = "devy"
    FIRST_DOWN_SCORING = "first_down_scoring"
    RETURN_SCORING = "return_scoring"
    WR_BONUS = "wr_bonus"
    NON_DYNASTY = "non_dynasty"


RULE_SUPPORT_MATRIX: dict[FormatRule, tuple[RuleSupportLevel, str, bool]] = {
    FormatRule.SUPERFLEX: ("supported", "Fully modeled", False),
    FormatRule.TEP: ("supported", "TE bonus modeled in valuation", False),
    FormatRule.HALF_PPR: ("supported", "Half-PPR modeled", False),
    FormatRule.FULL_PPR: ("supported", "Full-PPR modeled", False),
    FormatRule.STANDARD: ("supported", "Standard scoring modeled", False),
    FormatRule.MEDIAN_WINS: (
        "partially_supported",
        "Win-now urgency not median-adjusted",
        True,
    ),
    FormatRule.BEST_BALL: ("unsupported", "Best ball changes all lineup logic", True),
    FormatRule.IDP: ("unsupported", "Defensive players not valued", True),
    FormatRule.SALARY_CAP: ("unsupported", "Contract constraints not modeled", True),
    FormatRule.DEVY: ("unsupported", "College prospects not in player pool", True),
    FormatRule.FIRST_DOWN_SCORING: (
        "partially_supported",
        "First-down value not in player scores",
        True,
    ),
    FormatRule.RETURN_SCORING: (
        "partially_supported",
        "Return specialist value not modeled",
        True,
    ),
    FormatRule.WR_BONUS: (
        "partially_supported",
        "WR bonus not reflected in positional multipliers",
        True,
    ),
    FormatRule.NON_DYNASTY: (
        "unsupported",
        "Tool is dynasty-only; pick/youth values invalid",
        True,
    ),
}

TRUST_MODIFIER_FULL_SUPPORT = 1.00
TRUST_MODIFIER_PARTIAL_SUPPORT = 0.75
TRUST_MODIFIER_UNSUPPORTED = 0.50

