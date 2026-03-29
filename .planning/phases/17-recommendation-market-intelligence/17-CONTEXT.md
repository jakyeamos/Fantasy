# Phase 17: Recommendation Contract & Market Intelligence - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Every major module emits structured recommendation cards with a consistent contract. An anti-overreaction layer protects elite assets from one-year noise (in both directions). Player context flags are tracked from a real data source and alter recommendations downstream. A market-vs-model gap layer is visible across all decision surfaces.

Existing output shapes are preserved — recommendation cards are emitted *alongside* existing API responses as `recommendation_cards: []`, not as replacements. All modules are in scope in one pass; where foundation is missing in a downstream phase, a TODO is added to that phase's plan.

</domain>

<decisions>
## Implementation Decisions

### Recommendation card emission
- **D-01:** Recommendation cards are emitted **alongside** existing output shapes — every relevant API response gains a `recommendation_cards: list[RecommendationCard]` field; existing fields (e.g., `TradeEvaluation.strategic_distinction`, `DimensionScore`) are not removed but replaced where the card is more complete and actionable
- **D-02:** **All major modules** are in scope this phase: trade, lineup/hygiene, direction/scorecard, picks, waiver, rookie, and orphan intake; where a module lacks sufficient foundation (e.g., a data dependency not yet built), a TODO is added in the relevant phase plan — not deferred from Phase 17
- **D-03:** `cta_destination` is a **route key or path string** — the backend emits intent (e.g., `/league/{league_id}/trade`); the frontend owns CTA routing logic; backend does not embed deep-link URLs
- **D-04:** Where a partial recommendation shape already exists (e.g., `strategic_distinction` in `TradeEvaluation`), it is **replaced** by the full `RecommendationCard` if the card is more actionable and educational; both coexisting is only acceptable during a transient migration step

### Priority ranking formula
- **D-05:** Priority formula is `priority = impact × confidence × execution × urgency` per REC-04; the formula applies uniformly across all modules — same weights, not module-specific
- **D-06:** `supporting_factors[]` follows REC-02: each factor carries `factor_name`, `direction` (positive/negative/neutral), `magnitude`, `explanation`

### Anti-overreaction layer
- **D-07:** The layer applies to **both** the underlying `PlayerValue` component scores AND the recommendation card output — it is not a display-layer filter; it gates score movements at the model level
- **D-08:** "Elite" is defined by a **combination** of `PlayerValue` scores (not a single field) — the exact composite threshold is Claude's discretion during planning/research; a combination approach is preferred because it enables detection of undervalued elite players whose `comp_insulation` may be moderate but overall profile is strong
- **D-09:** When the layer fires, stabilization is **silent** — only the final stabilized conclusion is shown on the recommendation card; no "insulation prior applied" annotation is surfaced to the user
- **D-10:** The layer applies **bidirectionally** — it dampens bearish overcorrection on elite players (protects from one-year dip overclaiming) AND dampens bullish overclaiming on low-insulation breakout candidates (prevents false ceiling signals)

### Player context flags
- **D-11:** Flags are sourced from a **real data feed** — not manual entry; the researcher identifies the best source (nfl_data_loader extension, Sleeper depth-chart endpoints, or an external NFL data API)
- **D-12:** Flags are **player-scoped** (global across all leagues), not league-scoped
- **D-13:** A context flag **always** triggers a change on the recommendation card — no materiality gate; even a minor flag adds at minimum one entry to `supporting_factors[]`
- **D-14:** Flags **expire automatically** — the researcher/planner defines expiry logic (roster change detected on next ingest, N-week TTL, or calendar-state transition); no manual clearance required

### Market value & model-vs-market gap
- **D-15:** External market data is **introduced this phase** — an external signal (KTC, FantasyCalc, or Sleeper ADP) is used as the **baseline market signal**; league trade history (revealed preferences from actual trades) is the **primary signal** for the final market value lens
- **D-16:** `lens_market` in `PlayerValue` becomes a true market-calibrated value (external baseline + league revealed preference weighting), not a model-derived estimate
- **D-17:** "Manager-demand value" (MKT-01) is implemented via whichever approach is more effective — either extending the Phase 12 pick-premium signal to cover all players (not just picks), or building a new per-player demand model from trade transaction history; Claude determines this during research
- **D-18:** Gap classification cutoffs (MKT-03: buy low / sell high / hold despite weak market / ignore false discount / market right model cautious / league-specific opportunity) are **Claude's discretion** — no user-defined thresholds
- **D-19:** "Hold despite weak market" is a valid first-class conclusion, not a fallback — it is surfaced with the same prominence as buy/sell signals

### Claude's Discretion
- Composite elite-tier threshold definition (D-08) — specific score combination and cutoff values
- Which external market data source to integrate (KTC vs. FantasyCalc vs. Sleeper ADP) — based on data quality, API stability, and freshness
- Whether manager-demand value extends Phase 12 or builds a new per-player demand model (D-17)
- Context flag expiry logic: TTL duration, ingest-triggered expiry, or calendar-state transition (D-14)
- Alembic migration numbering (must not conflict with 015–018 already in use)
- DB schema for context flags table, market value columns, and recommendation card storage
- Whether `RecommendationCard` is stored in DB or computed on demand (storage vs. latency tradeoff)

</decisions>

<specifics>
## Specific Ideas

- The anti-overreaction layer's silent behavior is deliberate — users should see a confident, stabilized recommendation, not a hedged one with visible model internals. The system should "have done the work" and show the result.
- Market value sourcing: league trade history is the ground truth. When a player gets traded in this league for X, that revealed preference should dominate a generic ADP signal. External signals fill gaps where no league-specific trades exist.
- Context flags must flow into `supporting_factors[]` — even if a flag is minor, it should appear. The card is the educational surface; flags are part of explaining why a recommendation is what it is.
- All modules in one pass is intentional — the goal is a uniform contract. Partial adoption creates inconsistency that the UX layer (Phase 20) cannot work around.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 17 requirements
- `.planning/REQUIREMENTS.md` §REC-01 through REC-06 — full recommendation contract spec (15 required fields, supporting_factors contract, confidence contract, priority formula, anti-overreaction triggers, context flag types)
- `.planning/REQUIREMENTS.md` §MKT-01 through MKT-05 — parallel values spec, model-vs-market gap spec, gap classification types, surface visibility requirements
- `.planning/ROADMAP.md` §Phase 17 — goal, 6 success criteria, dependency on Phase 16

### Existing output models (primary retrofit targets)
- `backend/src/fantasy/trade/models.py` — `TradeEvaluation`, `DimensionScore`, `StrategicDistinction`, `RerouteResult`, `PackageBuilderResult`; Phase 17 adds `recommendation_cards` to `TradeEvaluation`
- `backend/src/fantasy/intelligence/models.py` — `PlayerValue` (12 components, 5 lenses including `lens_market`), `TeamScorecard`, `DirectionResult`; Phase 17 modifies `lens_market` and adds anti-overreaction to `PlayerValue` computation
- `backend/src/fantasy/lineup/models.py` — `LineupResult`, hygiene suggestion models; Phase 17 adds `recommendation_cards`
- `backend/src/fantasy/waiver/models.py` — `WaiverRecommendation`; Phase 17 adds `recommendation_cards`
- `backend/src/fantasy/rookie/models.py` — `RookieBoardResult`, `DraftRoomResult`; Phase 17 adds `recommendation_cards`

### Existing context infrastructure
- `backend/src/fantasy/context/models.py` — `RecommendationContext`, `FreshnessTag`, `CalendarContext`; Phase 17 `RecommendationCard` extends or coexists with this
- `backend/src/fantasy/context/` — calendar service, freshness service, context repo; Phase 17 context flags may extend this module or live in a new `player_flags/` module

### Valuation engine (anti-overreaction integration point)
- `backend/src/fantasy/intelligence/valuation_engine.py` — `compute_player()` and `compute_all()`; anti-overreaction layer applies at the component score level inside this engine
- `backend/src/fantasy/intelligence/models.py` — `PlayerValue.comp_insulation` is one input to the elite composite; `comp_ceiling`, `comp_floor`, `lens_direction` are candidate additional inputs

### Phase 12 manager demand signals (possible extension for MKT-01)
- `.planning/phases/12-manager-rookie-pick-profiles/12-CONTEXT.md` — D-12 through D-17: pick-premium scoring logic, value-delta extension pattern, evidence thresholds
- `backend/src/fantasy/profiling/profiling_engine.py` — value-delta logic; candidate reuse for per-player manager-demand scoring

### Phase 14 trust infrastructure (pattern reference for flag ingestion)
- `.planning/phases/14-trust-infrastructure/` — trust format scanner and acknowledgment pattern; researcher should evaluate whether player context flags use a similar ingestion pipeline or a fully separate one

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PlayerValue` (12 components + 5 lenses): anti-overreaction layer modifies component scores inside `ValuationEngine.compute_player()` — no new model needed, gate applied at computation time
- `RecommendationContext` in `context/models.py`: already attached to `TradeEvaluation`; `RecommendationCard` is a new parallel model, not a replacement for `RecommendationContext`
- `DimensionScore` pattern: existing `confidence: Literal["HIGH", "MEDIUM", "LOW"]` + `reasoning` — the new `RecommendationCard` confidence contract (REC-03) follows the same Literal pattern
- Phase 12 pick-premium value-delta logic in `profiling_engine.py`: candidate reuse for manager-demand value computation if the "extend Phase 12" approach is chosen for D-17

### Established Patterns
- `recommendation_cards: list[...] | None = None` field pattern: matches existing optional fields on `TradeEvaluation` (`reroutes`, `package`) — new card field follows the same optional-list pattern
- Literal union contracts: Phase 11 established strict Literal unions for API contracts (title-window labels, hygiene action types) — `RecommendationCard.recommendation_type` and gap classification follow the same pattern
- Engine isolation: each engine is a separate class injected into `IntelligenceService`; a new `RecommendationCardEngine` or `MarketGapEngine` follows the same injection pattern

### Integration Points
- `ValuationEngine.compute_player()` — anti-overreaction layer is applied here, before scores are written; same function, new stabilization step
- All major routers (`/trade`, `/intelligence`, `/lineup`, `/profiling`, `/picks`, `/waiver`, `/rookie-board`, `/startup`) — each gains a `recommendation_cards` field on its primary response model
- `trades` table: primary data source for league-revealed market preferences (D-15) — same table Phase 12 used for pick-premium; Phase 17 extends that read to cover all player-for-player trades
- `players` table: player context flags table will likely join against this; `player_id` is the foreign key

</code_context>

<deferred>
## Deferred Ideas

- User-configurable anti-overreaction sensitivity (e.g., "be more aggressive on my contender team") — Phase 20 UX layer or later
- Cross-league market gap comparison (does this player's league-specific value differ meaningfully from the model's cross-league view?) — Phase 18/19 context
- Surfacing which specific trades drove the league market value signal (market transparency) — useful but not in Phase 17 scope
- Manual context flag override / admin entry fallback — Phase 14 pattern; consider only if real data source proves unreliable

</deferred>

---

*Phase: 17-recommendation-market-intelligence*
*Context gathered: 2026-03-28*
