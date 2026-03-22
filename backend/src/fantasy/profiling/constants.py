from __future__ import annotations

MIN_TRADE_EVIDENCE_THRESHOLD: int = 10
SECONDARY_TYPE_THRESHOLD_RATIO: float = 0.40

ADP_FALLBACK_BY_POSITION: dict[str, float] = {
    "QB": 0.05,
    "RB": 0.05,
    "WR": 0.05,
    "TE": 0.03,
    "K": 0.01,
    "DEF": 0.01,
    "UNKNOWN": 0.03,
}

PICK_VALUE_NORMALIZED: dict[int, float] = {
    1: 0.70,
    2: 0.45,
    3: 0.25,
    4: 0.10,
}

EXPLOITATION_TYPE_WEIGHTS: dict[str, float] = {
    "value_loss": 0.40,
    "timing_error": 0.25,
    "directional_incoherence": 0.20,
    "archetype_overpay": 0.15,
}

EXPLOITATION_TYPE_LABELS: dict[str, str] = {
    "value_loss": "value-loss trader",
    "timing_error": "timing-error trader",
    "directional_incoherence": "directionally-incoherent trader",
    "archetype_overpay": "archetype-specific overpayer",
}

PITCH_ARCHETYPES: dict[str, dict[str, str]] = {
    "value_loss_win_now": {
        "deal_archetype": "Win-now swap",
        "send_template": "aging starter plus a later pick",
        "avoid_template": "future-value heavy offers",
        "reasoning_template": "This manager has repeatedly lost market value while chasing immediate points. Offer stable veteran production and press for stronger long-term insulation.",
    },
    "value_loss_rebuild": {
        "deal_archetype": "Rebuild accelerator",
        "send_template": "mid pick plus surplus depth",
        "avoid_template": "older short-term scorers",
        "reasoning_template": "This manager loses value even while reshaping the roster. Picks and bench insulation can usually beat their valuation threshold.",
    },
    "incoherent_seller": {
        "deal_archetype": "Pick acquisition",
        "send_template": "roster-balancing veteran",
        "avoid_template": "same-round pick swaps",
        "reasoning_template": "Their trade history breaks from their stated direction. Offer the type of veteran they should not want and buy future flexibility cheaply.",
    },
    "archetype_overpayer_qb": {
        "deal_archetype": "QB premium extraction",
        "send_template": "QB2 or volatile quarterback depth",
        "avoid_template": "non-QB centerpieces",
        "reasoning_template": "They have shown a repeated willingness to overpay for quarterback help. Lead with QB depth and insist on insulation coming back.",
    },
    "timing_error_contender": {
        "deal_archetype": "Recency spike sale",
        "send_template": "recent producer at perceived peak",
        "avoid_template": "buy-low injured assets",
        "reasoning_template": "This contender reacts to short-term scoring swings. Use recent production spikes to move aging assets before the market mean reverts.",
    },
    "timing_error_rebuild": {
        "deal_archetype": "Trough buyback",
        "send_template": "pick-based patience offer",
        "avoid_template": "production-only veterans",
        "reasoning_template": "This rebuilder has sold assets at bad timing points before. Patient pick-plus-depth offers are more likely to land than headline veteran packages.",
    },
}
