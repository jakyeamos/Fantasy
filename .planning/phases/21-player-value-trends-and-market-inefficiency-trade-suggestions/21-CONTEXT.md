# Phase 21: Player Value Trends & Market Inefficiency Trade Suggestions - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

A projection model tracks each player's raw component scores and startup ADP year-over-year, produces a season-over-season "will rise / will maintain / will fall" forecast grounded in historical positional data, and surfaces that forecast in two places: (1) a cross-league opportunity feed that surfaces proactive buy/sell moves ranked by impact score, and (2) Phase 17 recommendation cards, where trend signals enrich `supporting_factors[]` and weaken the anti-overreaction stabilization prior when warranted. This phase does NOT add a new valuation model or replace Phase 17's gap classification — it adds the temporal dimension that Phase 17 currently lacks.

</domain>

<decisions>
## Implementation Decisions

### Trend signal scope

- **D-01:** Track all **12 raw component scores** (not the 5 lenses) plus **startup ADP year-over-year** as the external market signal. Components give projection granularity; startup ADP gives the market-side anchor.
- **D-02:** Temporal scope is **season-over-season historical comparison** — this is a projection model informed by what players at this position with this component profile have historically done in the following season. Not a rolling snapshot window.
- **D-03:** Output is **both**: continuous delta stored internally; labeled as `"will rise" / "will maintain" / "will fall"` on all output surfaces. Labels are projection-framed ("will"), not trailing-framed ("has risen") — this is primarily an offseason feature.
- **D-04:** Players with no snapshot history are **backfilled** from fantasy and statistical data. There is sufficient historical fantasy and statistical data to populate component proxies for any active player.

### Opportunity feed surface

- **D-05:** Feed is **cross-league**, sorted by **impact score** (gap magnitude × projection confidence). An ownership symbol on each card indicates which of the user's leagues they hold the player in. Players not owned appear without the ownership symbol — they are buy targets.
- **D-06:** Opportunity card fields: player name/position, trend label (`will rise / will maintain / will fall`), gap vs. current startup ADP, suggested action (buy / sell / hold), leagues owned in (with symbol), **similar players with similarity score and context** (why they are comparable — position, archetype, trajectory), and projection confidence indicator.
- **D-07:** Rank is driven by **opportunity urgency** (gap magnitude × projection confidence). Rank only changes when there is evidence the next dynasty calendar state will affect the market (e.g., combine results pending, NFL Draft approaching, trade deadline opening). No time-based decay.
- **D-08:** **One unified list** — buy-side and sell-side opportunities appear together, distinguished by suggested action label. No separate tabs.

### Phase 17 integration

- **D-09:** Trend adds **supporting context only** to Phase 17 recommendation cards — it appears as entries in `supporting_factors[]` with `factor_name`, `direction`, `magnitude`, and `explanation`. The gap classification label itself does not change.
- **D-10:** **Conflict case** (e.g., Phase 17 says "buy low" but trend says "will fall", or Phase 17 says "sell high" but trend says "will rise") → the recommendation card surfaces a **detailed conflict explanation** inline. No automatic override — the user sees the tension and decides.
- **D-11:** `"will fall"` trend on an elite player **weakens the anti-overreaction stabilization prior** from Phase 17's REC-05 layer. The stabilization is not removed entirely, but its dampening strength is reduced proportionally to the trend confidence level.
- **D-12:** Trend signals are **available inside Phase 17 recommendation cards** — the researcher/planner must wire the trend engine output into all Phase 17 card-emitting modules (trade, lineup, hygiene, picks, rookie, waiver).

### Trigger logic

- **D-13:** Trigger is a **combination of gap + trend**, but both do not need to point the same direction. Example: a veteran player with "will fall" trend can still surface as a buy-low opportunity for a contending team that needs current production. The suggested action accounts for direction-fit context, not just value direction.
- **D-14:** **Gap magnitude always determines surfacing.** A large gap with low-confidence projection surfaces (flagged as low confidence). A small gap with high-confidence projection does not surface unless it crosses the gap threshold. Gap magnitude is the primary gate; confidence modulates the flag, not the visibility.
- **D-15:** Rank changes only when there is **evidence the next calendar state will affect the market** (combine week, NFL Draft, trade deadline, rookie fever). No passive time-based decay or staleness ranking.
- **D-16:** **No player exclusions** from the feed. All players are eligible regardless of injury status, active context flags, or user ownership. The ownership symbol handles relevance filtering visually.

### Claude's Discretion

- Specific gap threshold values for surfacing (gap magnitude cutoff)
- Component score combinations that map to "will rise / will maintain / will fall" buckets — derived from historical positional analysis, not hardcoded
- Similarity score algorithm (what makes two players "similar" — position + archetype + trajectory proximity)
- How startup ADP year-over-year delta is normalized across positions
- Alembic migration numbering (must not conflict with migrations already in use through Phase 20)
- Whether trend data is stored per-player per-season in a new table or computed on demand from snapshot history

</decisions>

<specifics>
## Specific Ideas

- The veteran buy-low case is canonical: a player projected to decline in dynasty value is still a valid buy-low for a contending team that only needs 1–2 more seasons of production. The card must surface direction-fit context alongside the trend, not just the trend alone.
- "Similar players" on the opportunity card serves two purposes: (1) alternative targets if the user can't acquire the primary player, (2) supporting evidence that the projection is grounded ("historically, players with this profile at age 28 follow this trajectory — here are the comps").
- Conflict explanations (D-10) should be treated as first-class content, not footnotes. If Phase 17 and Phase 21 disagree, that tension is useful information — the user should see both sides clearly, not just the primary conclusion.
- Calendar-state-aware rank changes (D-15) are the offseason version of urgency. "Combine week is approaching — WR prospects with upside scores in this band have historically spiked in ADP after combine" is the kind of rank escalation this enables.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 21 scope
- `.planning/ROADMAP.md` §Phase 21 — phase goal stub and dependency on Phase 20

### Phase 17 integration contracts (primary retrofit targets)
- `.planning/REQUIREMENTS.md` §REC-01 through REC-06 — recommendation card contract, `supporting_factors[]` schema, anti-overreaction (REC-05) stabilization logic
- `.planning/REQUIREMENTS.md` §MKT-01 through MKT-05 — parallel values spec, model-vs-market gap classification types
- `.planning/phases/17-recommendation-market-intelligence/17-CONTEXT.md` — D-07 through D-10 (anti-overreaction bidirectionality, elite definition, silent stabilization), D-15 through D-19 (market value sourcing, gap classification)

### Existing valuation and component models
- `backend/src/fantasy/intelligence/models.py` — `PlayerValue` (12 components, 5 lenses); Phase 21 trend engine reads component scores and produces trend output alongside this model
- `backend/src/fantasy/intelligence/valuation_engine.py` — `compute_player()` and `compute_all()`; anti-overreaction stabilization lives here — Phase 21 weakens the prior when trend is "will fall" (D-11)

### Calendar state (for rank change triggers)
- `backend/src/fantasy/context/models.py` — `CalendarContext`, calendar state definitions; Phase 21 rank escalation logic keys off calendar state transitions
- `backend/src/fantasy/context/calendar_service.py` — active calendar state resolution

### Snapshot infrastructure (historical component data)
- `backend/src/fantasy/snapshots/snapshot_service.py` — existing snapshot capture logic; Phase 21 reads historical snapshots for component score trajectory

### Phase 8 comps pattern (similarity score reference)
- `.planning/phases/08-historical-prospect-lab/08-CONTEXT.md` — archetype clustering and historical comps methodology; Phase 21 similarity score should align with or reuse this pattern where applicable
- `backend/src/fantasy/prospects/models.py` — `archetype_label` and comp fields; candidate reuse for similar-player logic

### Schema
- Triple-write pattern required for any new tables: Alembic migration + `startup_tasks.py` `_SCHEMA_COMPAT_TABLES` + `conftest.py` test schema bootstrap
- Next migration number must not conflict with Phase 15 (018), Phase 16 (019), Phase 17 (020–021) — researcher must verify current head

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ValuationEngine.compute_player()`: produces all 12 component scores per player — Phase 21 trend engine reads this output and builds season-over-season deltas
- `CalendarService`: active calendar state resolution — reuse to gate rank escalation logic (D-15)
- `SnapshotService`: existing snapshot capture — historical component snapshots are the primary data source for trend derivation
- Phase 8 archetype clustering (if executed): `archetype_label` and comp methodology in `prospects/` package — candidate reuse for Phase 21 similarity scoring

### Established Patterns
- `supporting_factors[]` with `factor_name / direction / magnitude / explanation`: Phase 17's contract; Phase 21 must emit trend entries in this exact shape
- Literal union contracts (Phase 11, Phase 17): `"will rise" / "will maintain" / "will fall"` labels should follow the same `Literal["will_rise", "will_maintain", "will_fall"]` pattern
- Engine injection pattern: new `TrendEngine` and `OpportunityFeedEngine` follow the same class-injected-into-service pattern used by existing engines

### Integration Points
- `ValuationEngine.compute_player()` — anti-overreaction weakening (D-11) applied here when trend output is "will fall" for elite player
- All Phase 17 card-emitting engines (TradeEngine, LineupEngine, HygieneEngine, etc.) — trend `supporting_factors[]` wired into their card output
- New `/opportunities` route (or similar) — opportunity feed API endpoint serving the cross-league surface
- `players` table — startup ADP year-over-year delta likely stored here or in a new `player_trends` table

</code_context>

<deferred>
## Deferred Ideas

- User-configurable trend confidence thresholds ("surface even low-confidence moves") — Phase 20 UX settings layer or later
- Per-league opportunity feed filtering beyond the ownership symbol — deferred; cross-league unified view is sufficient in Phase 21
- Trend-based pick valuation (how does a player's projected value trajectory affect the picks used to trade for them) — could integrate with Phase 6 pick engine; defer to a future phase
- Historical opportunity feed accuracy grading (did the system's buy-low calls actually pay off?) — aligns with Phase 9 retrospectives; defer

</deferred>

---

*Phase: 21-player-value-trends-and-market-inefficiency-trade-suggestions*
*Context gathered: 2026-03-31*
