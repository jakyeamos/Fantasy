from __future__ import annotations

from typing import Literal

CalendarState = Literal[
    "startup",
    "preseason",
    "early_season",
    "trade_deadline",
    "playoffs",
    "rookie_fever",
    "post_combine",
    "post_nfl_draft",
]

CALENDAR_WINDOWS: list[tuple[int, int, int, int, str]] = [
    (4, 23, 5, 15, "post_nfl_draft"),
    (2, 24, 3, 10, "post_combine"),
    (1, 13, 4, 22, "rookie_fever"),
    (11, 22, 1, 12, "playoffs"),
    (11, 1, 11, 21, "trade_deadline"),
    (7, 15, 8, 28, "preseason"),
    (8, 29, 10, 31, "early_season"),
]

FALLBACK_STATE: str = "early_season"
OVERRIDE_TTL_DAYS: int = 30

FRESHNESS_THRESHOLDS: dict[str, int] = {
    "injuries": 48,
    "depth_chart": 168,
    "free_agency": 72,
    "combine": 24,
    "draft_capital": 24,
    "landing_spots": 168,
}

CALENDAR_GUIDANCE: dict[tuple[str, str], str] = {
    ("rookie_fever", "pick_sell"): "Peak rookie fever window - selling now maximizes return before draft inflation spreads across the market.",
    ("rookie_fever", "pick_hold"): "Already in the peak window - hold only with a strong class conviction.",
    ("post_nfl_draft", "pick_sell"): "Post-draft landing-spot hype is live - move picks quickly before the market normalizes.",
    ("post_combine", "pick_sell"): "Combine winners are spiking - sell into the athletic hype before it cools.",
    ("trade_deadline", "veteran_sell"): "Trade deadline window - contenders are paying up for proven weekly points.",
    ("playoffs", "veteran_sell"): "Playoff push - win-now teams often stretch past fair value for short-term starters.",
    ("preseason", "veteran_buy"): "Camp noise creates veteran discounts - this is a buying window.",
    ("early_season", "pick_buy"): "Early season is typically the cheapest annual window for future picks.",
    ("post_nfl_draft", "general"): "Post-NFL Draft: landing spots are set, so refresh rookie values before making a move.",
    ("rookie_fever", "general"): "Rookie fever is active - picks and prospects are elevated versus long-run baselines.",
    ("trade_deadline", "general"): "Trade deadline pressure is building - contenders buy urgency while rebuilders should sell into it.",
    ("playoffs", "general"): "Playoff incentives distort market prices - separate short-term urgency from long-term value.",
    ("preseason", "general"): "Preseason volatility can create false certainty - treat camp headlines carefully.",
    ("early_season", "general"): "Early-season usage shifts fast - exploit market overreactions before they settle.",
}

