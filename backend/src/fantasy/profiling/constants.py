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

PITCH_ANGLE_VARIANTS: dict[str, tuple[dict[str, str], ...]] = {
    "value_loss_rebuild_pick_pressure": (
        {
            "deal_archetype": "Future-flex buyback",
            "send_template": "liquid veterans and depth that preserve your best picks",
            "avoid_template": "offers that ask them to move another premium future pick",
            "reasoning_template": "They are on a {direction_label} path but still sent picks in {sent_pick_trades} recent deals. Sell usability, then make the return about getting future insulation back.",
        },
        {
            "deal_archetype": "Pick-leak recovery",
            "send_template": "older starters with a small sweetener",
            "avoid_template": "all-pick structures that let them reset too cleanly",
            "reasoning_template": "This roster keeps leaking future flexibility during a {direction_label} cycle. Frame the deal around reclaiming insulation, not winning the headline on points.",
        },
    ),
    "value_loss_rebuild_insulation": (
        {
            "deal_archetype": "Rebuild insulation squeeze",
            "send_template": "mid picks plus surplus depth",
            "avoid_template": "older short-term scorers with no reroll value",
            "reasoning_template": "They have lost value in {negative_trade_phrase} deals while trying to reshape the roster. Packages that add insulation and optionality should clear their threshold more often than splashy veterans.",
        },
        {
            "deal_archetype": "Portfolio rebalance",
            "send_template": "bench depth and flexible picks",
            "avoid_template": "one-asset blockbuster offers",
            "reasoning_template": "The pattern is not just losing trades, it is losing flexibility during a {direction_label}. Lean into multi-piece offers that make the roster easier to reroute later.",
        },
    ),
    "value_loss_contender_points_patch": (
        {
            "deal_archetype": "Points-patch tax",
            "send_template": "bankable weekly production and lineup stability",
            "avoid_template": "future-value heavy packages with delayed payoff",
            "reasoning_template": "They have lost value in {negative_trade_phrase} deals while chasing usable points. Put immediate lineup help on the table and charge extra future insulation for it.",
        },
        {
            "deal_archetype": "Standings pressure swap",
            "send_template": "aging starters who solve a weekly problem",
            "avoid_template": "slow-burn upside bets",
            "reasoning_template": "This profile keeps paying for short-term certainty. When the need is points now, stable veteran production can pull back better long-range value than the market should allow.",
        },
    ),
    "value_loss_contender_future_leak": (
        {
            "deal_archetype": "Future-value clawback",
            "send_template": "productive veterans plus a modest add-on",
            "avoid_template": "packages centered on youth and patience",
            "reasoning_template": "They are competing, but the trade history still leaks long-term value. Offer production they can start immediately and make them pay to move future flexibility off your side.",
        },
        {
            "deal_archetype": "Win-now premium extraction",
            "send_template": "usable points with low long-term shelf life",
            "avoid_template": "offers that improve them without extracting insulation",
            "reasoning_template": "A contender who keeps bleeding market value is usually buying comfort. Sell comfort, then insist that the price comes back in picks or younger insulation.",
        },
    ),
    "timing_error_rebuild_patience": (
        {
            "deal_archetype": "Patience-over-points frame",
            "send_template": "pick-based patience and reroll depth",
            "avoid_template": "production-only veterans",
            "reasoning_template": "Their {direction_label} has shown timing mistakes before. Slow, patient offers tend to land better than headline veterans when a rebuilder has already sold too early.",
        },
        {
            "deal_archetype": "Trough buyback",
            "send_template": "steady depth plus future insulation",
            "avoid_template": "recent spike producers",
            "reasoning_template": "This roster has reacted poorly to market troughs. Buy from that impatience by keeping the package calm, flexible, and centered on future utility.",
        },
    ),
    "timing_error_rebuild_trough_buyback": (
        {
            "deal_archetype": "Market-trough pounce",
            "send_template": "quiet picks and depth while sentiment is cold",
            "avoid_template": "bidding wars around the latest points spike",
            "reasoning_template": "The timing issue here is not direction, it is impatience. Attack the moments when value is depressed and let the market reset work in your favor.",
        },
        {
            "deal_archetype": "Cold-market accumulation",
            "send_template": "future-facing offers with flexible exit paths",
            "avoid_template": "packages built around box-score headlines",
            "reasoning_template": "They have shown a habit of moving assets when sentiment cools. Calm offers with reroll value should beat louder packages built around recent production.",
        },
    ),
    "timing_error_contender_spike_sale": (
        {
            "deal_archetype": "Recency spike sale",
            "send_template": "recent producers at perceived peak value",
            "avoid_template": "buy-low injured assets",
            "reasoning_template": "This contender reacts to short-term scoring swings. Use recent production spikes to move aging assets before the market mean reverts.",
        },
        {
            "deal_archetype": "Hot-box-score flip",
            "send_template": "players coming off visible scoring weeks",
            "avoid_template": "long-horizon stash pieces",
            "reasoning_template": "When the room is chasing points, the cleanest pitch is a player who just solved a problem on paper. Sell the spike before the weekly urgency fades.",
        },
    ),
    "timing_error_contender_box_score": (
        {
            "deal_archetype": "Box-score leverage",
            "send_template": "stable veterans whose value is boosted by recent output",
            "avoid_template": "asset clusters that require patience",
            "reasoning_template": "Their timing pattern suggests box-score decisions more than market discipline. Lead with players whose recent production does the selling for you.",
        },
        {
            "deal_archetype": "Weekly panic premium",
            "send_template": "lineup patches with immediate scoring visibility",
            "avoid_template": "future-only sweeteners",
            "reasoning_template": "This manager buys certainty when weekly pressure rises. Clear starter points are more persuasive here than theoretical upside.",
        },
    ),
    "directional_incoherence_pick_drift": (
        {
            "deal_archetype": "Direction-drift squeeze",
            "send_template": "veterans that look useful but slow down a {direction_label}",
            "avoid_template": "same-round pick swaps",
            "reasoning_template": "Their trade history keeps drifting away from the stated {direction_label}. Offer the type of veteran they should not want and pull back future flexibility cheaply.",
        },
        {
            "deal_archetype": "Misaligned roster reset",
            "send_template": "roster-balancing veterans with immediate usability",
            "avoid_template": "packages that help them cleanly recommit to the plan",
            "reasoning_template": "This is a direction problem more than a raw value problem. The best angle is usually an asset that feels helpful now but deepens the disconnect in their build.",
        },
    ),
    "directional_incoherence_reset": (
        {
            "deal_archetype": "Roster-logic correction",
            "send_template": "plug-and-play veterans that fit the current mood",
            "avoid_template": "offers that restore long-term coherence for them",
            "reasoning_template": "Their moves do not consistently match the roster story. If the manager is acting on impulse, sell the impulse and keep the cleaner long-term assets.",
        },
        {
            "deal_archetype": "Narrative mismatch trade",
            "send_template": "players that solve today's problem but complicate tomorrow",
            "avoid_template": "clean future-for-future exchanges",
            "reasoning_template": "This profile is vulnerable when the stated plan and the actual trade behavior split apart. Offer the asset that sounds right in the moment, not the one that truly fixes the build.",
        },
    ),
    "archetype_overpay_qb_patch": (
        {
            "deal_archetype": "QB patch premium",
            "send_template": "QB2 or volatile quarterback depth",
            "avoid_template": "non-QB centerpieces",
            "reasoning_template": "They have repeatedly paid up for quarterback help. Lead with QB depth and insist on insulation coming back.",
        },
        {
            "deal_archetype": "Quarterback room tax",
            "send_template": "startable quarterback insurance",
            "avoid_template": "packages that hide the QB value inside throw-ins",
            "reasoning_template": "When a manager keeps shopping for quarterback stability, the cleanest exploit is obvious supply. Sell a usable passer and make the return do the real work.",
        },
    ),
    "archetype_overpay_qb_ceiling": (
        {
            "deal_archetype": "Quarterback ceiling tax",
            "send_template": "high-variance QB depth with upside weeks",
            "avoid_template": "safe non-quarterback depth pieces",
            "reasoning_template": "This is not generic overpay behavior, it is targeted demand for quarterback upside. Make the ceiling story loud and the price even louder.",
        },
        {
            "deal_archetype": "Superflex panic sale",
            "send_template": "volatile passers with visible spike-week access",
            "avoid_template": "slow two-for-two offers",
            "reasoning_template": "Managers who repeatedly chase quarterbacks usually care about avoiding zeros as much as adding points. Package that fear and charge a premium for solving it.",
        },
    ),
    "archetype_overpay_position": (
        {
            "deal_archetype": "{focus_position_label} premium extraction",
            "send_template": "{focus_asset_phrase}",
            "avoid_template": "offers that ignore the position they keep paying for",
            "reasoning_template": "They have repeatedly overpaid for {focus_position_label} help. Put that room under pressure and ask for insulation on the way back.",
        },
        {
            "deal_archetype": "{focus_position_label} demand tax",
            "send_template": "{focus_asset_phrase}",
            "avoid_template": "balanced offers with no positional hook",
            "reasoning_template": "The repeated spend is concentrated in the {focus_position_label} room, not spread across the roster. Sell that specific pain point rather than a generic package.",
        },
    ),
}
