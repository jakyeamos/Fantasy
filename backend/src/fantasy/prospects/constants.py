from __future__ import annotations

from typing import Literal


Position = Literal["QB", "RB", "WR", "TE"]
OutcomeBucket = Literal["hit", "mediocre", "bust"]

POSITIONS: list[Position] = ["QB", "RB", "WR", "TE"]

MIN_OUTCOME_SEASONS = 3
MIN_COMP_COUNT = 5
HISTORICAL_START_YEAR = 2011
CLUSTER_RANDOM_STATE = 42

OUTCOME_HIT: OutcomeBucket = "hit"
OUTCOME_MEDIOCRE: OutcomeBucket = "mediocre"
OUTCOME_BUST: OutcomeBucket = "bust"
OUTCOME_BUCKETS: list[OutcomeBucket] = [OUTCOME_HIT, OUTCOME_MEDIOCRE, OUTCOME_BUST]

QB_HIT_THRESHOLD = {"top_n": 6, "min_seasons": 2, "window": 4}
RB_HIT_THRESHOLD = {"top_n": 12, "min_seasons": 2, "window": 3}
WR_HIT_THRESHOLD = {"top_n": 24, "min_seasons": 2, "window": 4}
TE_HIT_THRESHOLD = {"top_n": 12, "min_seasons": 2, "window": 4}
HIT_THRESHOLDS = {
    "QB": QB_HIT_THRESHOLD,
    "RB": RB_HIT_THRESHOLD,
    "WR": WR_HIT_THRESHOLD,
    "TE": TE_HIT_THRESHOLD,
}

QB_MEDIOCRE = {"top_n": 6, "min_seasons": 1, "window": 4}
RB_MEDIOCRE = {"top_n": 24, "min_seasons": 1, "window": 3}
WR_MEDIOCRE = {"top_n": 36, "min_seasons": 1, "window": 4}
TE_MEDIOCRE = {"top_n": 24, "min_seasons": 1, "window": 4}
MEDIOCRE_THRESHOLDS = {
    "QB": QB_MEDIOCRE,
    "RB": RB_MEDIOCRE,
    "WR": WR_MEDIOCRE,
    "TE": TE_MEDIOCRE,
}

DRAFT_CAPITAL_TIERS = {
    "Tier 1": (1, 12),
    "Tier 2": (13, 36),
    "Day 2": (37, 72),
    "Day 3": (73, 255),
}

COMMON_FEATURES = ["age_at_draft", "draft_ovr", "forty", "weight", "height", "vertical"]
QB_FEATURES = COMMON_FEATURES + [
    "college_completion_pct_proxy",
    "college_passing_yards",
    "college_ypa",
    "college_pass_td_rate",
    "college_qb_rush_yards",
    "college_qb_rush_ypg",
    "college_scramble_rate",
]
RB_FEATURES = COMMON_FEATURES + [
    "bench",
    "college_rushing_yards",
    "college_rush_ypg",
    "college_ypc",
    "college_mkt_share_proxy",
    "college_td_rate",
]
WR_FEATURES = COMMON_FEATURES + [
    "cone",
    "college_receiving_yards",
    "college_rec_ypg",
    "college_yprr",
    "college_ypt",
    "college_mkt_share_proxy",
    "college_td_rate",
]
TE_FEATURES = COMMON_FEATURES + [
    "bench",
    "college_receiving_yards",
    "college_rec_ypg",
    "college_yprr",
    "college_mkt_share_proxy",
    "college_td_rate",
]

POSITION_FEATURES = {
    "QB": QB_FEATURES,
    "RB": RB_FEATURES,
    "WR": WR_FEATURES,
    "TE": TE_FEATURES,
}

CLUSTER_FEATURES = [
    "age_at_draft",
    "draft_ovr",
    "forty",
    "weight",
    "height",
    "vertical",
    "bench",
    "cone",
    "shuttle",
    "college_games",
    "college_targets",
    "college_receptions",
    "college_receiving_yards",
    "college_receiving_tds",
    "college_routes_run",
    "college_carries",
    "college_rushing_yards",
    "college_rushing_tds",
    "college_pass_attempts",
    "college_completions",
    "college_passing_yards",
    "college_passing_tds",
    "college_interceptions",
    "college_rec_ypg",
    "college_rush_ypg",
    "college_yprr",
    "college_ypt",
    "college_ypc",
    "college_ypa",
    "college_pass_td_rate",
    "college_qb_rush_yards",
    "college_qb_rush_tds",
    "college_qb_rush_ypg",
    "college_scramble_rate",
    "college_mkt_share_proxy",
    "college_td_rate",
    "college_completion_pct_proxy",
]

FEATURE_DISPLAY_NAMES = {
    "age_at_draft": "age",
    "draft_ovr": "draft capital",
    "forty": "speed",
    "weight": "size",
    "height": "size",
    "vertical": "athleticism",
    "bench": "strength",
    "cone": "agility",
    "shuttle": "agility",
    "college_games": "experience",
    "college_targets": "volume",
    "college_receptions": "volume",
    "college_receiving_yards": "receiving yards",
    "college_receiving_tds": "receiving touchdowns",
    "college_routes_run": "route volume",
    "college_carries": "carry volume",
    "college_rushing_yards": "rushing yards",
    "college_rushing_tds": "rushing touchdowns",
    "college_pass_attempts": "passing volume",
    "college_completions": "completion volume",
    "college_passing_yards": "passing yards",
    "college_passing_tds": "passing touchdowns",
    "college_interceptions": "turnovers",
    "college_rec_ypg": "college production",
    "college_rush_ypg": "college production",
    "college_yprr": "route efficiency",
    "college_ypt": "target efficiency",
    "college_ypc": "rush efficiency",
    "college_ypa": "pass efficiency",
    "college_pass_td_rate": "passing touchdown rate",
    "college_qb_rush_yards": "QB rushing volume",
    "college_qb_rush_tds": "QB rushing touchdowns",
    "college_qb_rush_ypg": "QB rushing upside",
    "college_scramble_rate": "scramble rate",
    "college_mkt_share_proxy": "market share",
    "college_td_rate": "scoring efficiency",
    "college_completion_pct_proxy": "accuracy",
}

POSITION_CLUSTER_COUNT = {"QB": 3, "RB": 4, "WR": 4, "TE": 3}

HIT_RATE_HIGH = "High hit rate"
HIT_RATE_MODERATE = "Moderate hit rate"
HIT_RATE_LOW = "Low hit rate"

ARCHETYPE_LABELS = {
    "QB": ("Pocket QB", "Dual Threat", "Processor"),
    "RB": ("Workhorse", "Explosive RB", "Passing-Down RB", "Power RB"),
    "WR": ("X Receiver", "Field Stretcher", "Slot Separator", "Contested Catch WR"),
    "TE": ("Inline TE", "Move TE", "Big Slot"),
}

SUB_FLAG_FEATURES = {
    "Draft Capital": ("draft_ovr", True),
    "Age": ("age_at_draft", True),
    "Production": ("college_rec_ypg", False),
    "Rush Production": ("college_rush_ypg", False),
    "Route Efficiency": ("college_yprr", False),
    "Target Efficiency": ("college_ypt", False),
    "Rush Efficiency": ("college_ypc", False),
    "Pass Efficiency": ("college_ypa", False),
    "Pass TD Rate": ("college_pass_td_rate", False),
    "QB Rushing": ("college_qb_rush_ypg", False),
    "Scramble Rate": ("college_scramble_rate", False),
    "Market Share": ("college_mkt_share_proxy", False),
    "Scoring Efficiency": ("college_td_rate", False),
    "Athletic Testing": ("forty", True),
    "Size": ("weight", False),
    "Accuracy": ("college_completion_pct_proxy", False),
}

DEFAULT_LEAGUE_ID = "__global__"
