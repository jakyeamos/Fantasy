# Phase 10: Pick Accuracy & Draft Order - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the universal inverse-standings assumption in the pick engine with a rule-aware draft-slot projection. Each connected league gets an explicit `LeagueDraftOrderRule` capturing non-playoff order basis, playoff-team ordering, and tiebreakers. Pick projections are blocked until the rule is fully configured. Every pick value surface cites the active rule with a clickable link to the editor. Lottery configuration and consolation/toilet-bowl exceptions are out of scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Default rule & league onboarding
- **D-01:** Pick projections are **blocked** until the draft order rule is fully configured — no silent inverse-standings default for new leagues
- **D-02:** Blocked pick surfaces show a **"Rule not configured" placeholder** (not a banner); the placeholder is clickable and navigates to the league settings rule editor
- **D-03:** **All fields must be complete** before projections unblock — a partially configured rule (e.g., non-playoff order set, playoff ordering not yet set) keeps projections blocked
- **D-04:** Each league is configured **independently** — no copy-from-league feature

### Lottery configuration
- **D-05:** **Lottery descoped entirely** — user does not play leagues with lottery draft order; `LeagueDraftOrderRule` model excludes lottery fields; rule editor excludes lottery UI

### Consolation / toilet-bowl exceptions
- **D-06:** **Consolation exceptions descoped** — `LeagueDraftOrderRule` model excludes consolation fields; rule editor excludes consolation UI

### Rule model scope
- **D-07:** `LeagueDraftOrderRule` captures three fields:
  1. **Non-playoff order basis** — `inverse_standings` or `max_points_for`
  2. **Playoff-team ordering** — how playoff teams are slotted (e.g., by finish, by record)
  3. **Tiebreaker** — how ties in the non-playoff ordering are broken
- **D-08:** Both `inverse_standings` and `max_points_for` are supported non-playoff order bases — user plays leagues using each

### Rule editor UI
- **D-09:** Editor lives in **league settings** (alongside existing scoring/format settings), not a separate tab
- **D-10:** **Single-page form** — all three fields visible at once; no wizard/stepper

### Rule citation display
- **D-11:** Citation uses the **same format everywhere** — consistent small inline text on all pick value surfaces (trade evaluator, picks list, draft room)
- **D-12:** Citation is **clickable** — navigates to league settings rule editor
- **D-13:** Citation text includes **both** order basis and playoff-team ordering rule (e.g., "Using: Max PF order · Playoff teams by finish")
- **D-14:** "Rule not configured" placeholder is **also clickable** (same navigation target as the configured-state citation)

### Claude's Discretion
- Exact field names and enum values for `LeagueDraftOrderRule` (e.g., how playoff ordering options are labeled)
- Whether `LeagueDraftOrderRule` is its own DB table or a JSONB column on `leagues`
- Exact slot-projection algorithm for max-PF ordering vs. inverse-standings (both must pass regression fixtures)
- How the pick engine receives the rule — injected into `PickValuationContext` or loaded by `PickRepo`
- Alembic migration numbering (must not conflict with 009–011 already in use)

</decisions>

<specifics>
## Specific Ideas

- The "Rule not configured" state is the critical onboarding moment — making it clickable directly to the editor removes all friction between seeing the gap and fixing it.
- Citation text at the bottom of a pick value card (e.g., "Using: Max PF order · Playoff teams by finish") follows the same small muted-foreground inline-reasoning pattern established in Phase 6 timing recommendations.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Draft order rules requirement
- `.planning/REQUIREMENTS.md` §FS-01 — full task breakdown: model fields, editor requirement, pick value update requirement, regression fixture scenarios
- `.planning/ROADMAP.md` §Phase 10 — goal, success criteria (5 criteria), phase dependency on Phase 9

### Pick engine (primary integration target)
- `.planning/phases/06-dynamic-pick-valuation/06-CONTEXT.md` — D-01/D-02 (class_strength hook architecture), code_context §Integration Points (PickValuationContext structure, `expected_draft_slot()` function); Phase 10 wraps or replaces `expected_draft_slot()` with rule-aware logic
- `backend/src/fantasy/picks/pick_engine.py` — `expected_draft_slot()` is the function to replace; `compute_pick_value()` is the entry point that must receive the rule
- `backend/src/fantasy/picks/models.py` — `PickValuationContext` and `PickValue` are the models to extend with rule context and citation text

### Existing league settings patterns
- `backend/src/fantasy/ingestion/sleeper_mapper.py` — `LeagueSettings` model (scoring/format settings); `LeagueDraftOrderRule` is a separate model attached per-league
- `backend/src/fantasy/repositories/league_repo.py` — league read/write patterns; draft order rule CRUD follows same approach

### UI patterns (for frontend consistency)
- `.planning/phases/03-core-dashboard/03-UI-SPEC.md` — spacing scale, typography, color tokens
- `.planning/phases/06-dynamic-pick-valuation/06-UI-SPEC.md` — timing reasoning inline text pattern (12px / `text-muted-foreground`) — rule citation follows same treatment
- `frontend/src/routes/league.$leagueId.tsx` — league drill-in route where settings editor is added

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/picks/pick_engine.py` `expected_draft_slot()`: Current inverse-standings slot projection — Phase 10 replaces this with a rule-dispatching function
- `backend/src/fantasy/picks/models.py` `PickValuationContext`: Add `draft_order_rule` field here so the engine can use it; `PickValue` gets a `rule_citation` string field for display
- `frontend/src/components/trade/DimensionScoreRow.tsx`: Inline reasoning string pattern — rule citation text reuses the same `text-muted-foreground text-xs` treatment
- shadcn `Select` / `RadioGroup` — appropriate for the 2-option non-playoff order basis field in the rule editor form

### Established Patterns
- `backend/src/fantasy/picks/constants.py` — new draft order constants (e.g., order basis enum values) go here
- `backend/src/fantasy/repositories/league_repo.py` — CRUD pattern for league-scoped data; rule save/load follows this
- `frontend/src/routes/league.$leagueId.tsx` — league settings expansion point; rule editor form section added here
- Alembic migration numbering: 001–011 already exist; next available is 012

### Integration Points
- `pick_engine.py` `expected_draft_slot()`: Must accept a `LeagueDraftOrderRule` and branch on `order_basis`; fallback when rule is `None` is to return `None` / blocked state, not inverse-standings
- `PickValue.rule_citation`: New string field populated by engine; consumed by all frontend pick display components
- League settings route: Needs a `DraftOrderRuleForm` section with save action wired to a new `/leagues/{id}/draft-order-rule` endpoint
- All existing pick value display components: Render `rule_citation` as small clickable text below the value; if absent, render "Rule not configured" in same position

</code_context>

<deferred>
## Deferred Ideas

- Lottery configuration — user does not play lottery leagues; excluded from Phase 10 scope
- Consolation / toilet-bowl exceptions — excluded from Phase 10 scope
- Copy draft order rule across leagues — excluded; each league configured independently

</deferred>

---

*Phase: 10-pick-accuracy-draft-order*
*Context gathered: 2026-03-23*
