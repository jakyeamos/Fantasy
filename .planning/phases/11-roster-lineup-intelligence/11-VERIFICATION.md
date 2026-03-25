---
phase: 11-roster-lineup-intelligence
verified: 2026-03-25T02:53:35Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "Taxi eligibility, IR occupancy, and manual exceptions are modeled per league"
    status: partial
    reason: "Taxi eligibility and IR occupancy are implemented per league, but no per-league manual exception model/field/path was found."
    artifacts:
      - path: "backend/src/fantasy/lineup/models.py"
        issue: "LeagueTaxiConfig has taxi slots/eligibility fields only; no manual exception fields."
      - path: "backend/src/fantasy/lineup/lineup_repo.py"
        issue: "Taxi config persistence covers slots/eligibility only; no manual exception persistence/read path."
      - path: "backend/alembic/versions/014_phase11_lineup_tables.py"
        issue: "league_taxi_configs table has no manual-exception column(s)."
    missing:
      - "Add per-league manual exception model fields and persistence."
      - "Expose manual exception configuration through leagues API and frontend config form."
  - truth: "Plan requirement IDs are fully accounted for in REQUIREMENTS.md"
    status: failed
    reason: "All phase plans declare FS-02 and FS-04, but those IDs are not defined in .planning/REQUIREMENTS.md."
    artifacts:
      - path: ".planning/phases/11-roster-lineup-intelligence/11-01-PLAN.md"
        issue: "requirements includes FS-02, FS-04."
      - path: ".planning/phases/11-roster-lineup-intelligence/11-02-PLAN.md"
        issue: "requirements includes FS-02, FS-04."
      - path: ".planning/phases/11-roster-lineup-intelligence/11-03-PLAN.md"
        issue: "requirements includes FS-02, FS-04."
      - path: ".planning/phases/11-roster-lineup-intelligence/11-04-PLAN.md"
        issue: "requirements includes FS-02, FS-04."
      - path: ".planning/REQUIREMENTS.md"
        issue: "No FS-02 / FS-04 entries found."
    missing:
      - "Define FS-02 and FS-04 in REQUIREMENTS.md or map plans to canonical requirement IDs that exist there."
---

# Phase 11: Roster & Lineup Intelligence Verification Report

**Phase Goal:** The system distinguishes a strong roster in abstract from a lineup that can actually win in the current format, and surfaces actionable low-level roster moves below the trade layer.
**Verified:** 2026-03-25T02:53:35Z
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | An optimal-starting-lineup calculator uses each league's real lineup constraints and scores starter strength by position against replacement-level baselines | ✓ VERIFIED | `LineupEngine.compute_all()` iterates active slots from `ScorecardInputs.roster_positions/starters`, computes per-position and flex replacement levels, and stores per-slot starter vs replacement scores. |
| 2 | A title-window score weights elite starter ceiling, lineup stability, and playoff-usable depth -- visible on each team screen | ✓ VERIFIED | Weighted composite in `lineup_engine.py` (`TITLE_WINDOW_WEIGHTS`, threshold labels) and rendered in `TitleWindowPanel` wired into `league.$leagueId.tsx`. |
| 3 | Team direction labels and trade recommendations can cite lineup-level reasons, not just aggregate roster value | ✓ VERIFIED | `IntelligenceService` applies lineup-derived "Outside Window" fragility nudge for contender labels; hygiene consolidation recommendations include player + counterparty rationale and package CTA. |
| 4 | Every team screen includes a roster-hygiene panel with stash, cut, move-to-taxi, and consolidation suggestions | ✓ VERIFIED | `RosterHygienePanel` filters/renders all 4 action types and route wiring places panel on overview for user roster. |
| 5 | Taxi eligibility, IR occupancy, and manual exceptions are modeled per league | ✗ FAILED | Taxi eligibility (`LeagueTaxiConfig`) and IR/taxi occupancy (`get_slot_occupancy`) exist; no manual exception model/column/API path found. |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/src/fantasy/lineup/lineup_engine.py` | Replacement-level lineup scoring and title-window classification | ✓ VERIFIED | Substantive compute paths + weighted classifier implemented and used by service. |
| `backend/src/fantasy/lineup/hygiene_engine.py` | Consolidate/cut/stash/taxi suggestions including counterparty context | ✓ VERIFIED | All four generators implemented; consolidation builds counterparty-aware recommendation. |
| `backend/src/fantasy/routers/intelligence.py` | API exposure for lineup/hygiene outputs | ✓ VERIFIED | GET `/intelligence/lineup/{league_id}/{roster_id}` and `/intelligence/hygiene/{league_id}/{roster_id}` present. |
| `backend/src/fantasy/routers/leagues.py` | Taxi config + slot occupancy API | ✓ VERIFIED | GET/PUT taxi-config and GET slot-occupancy endpoints present. |
| `frontend/src/components/lineup/TitleWindowPanel.tsx` | Team-screen title-window surface | ✓ VERIFIED | Query + loading/error/empty + label badge rendering implemented. |
| `frontend/src/components/lineup/LineupStrengthCard.tsx` | Position grid starter vs replacement surface | ✓ VERIFIED | Iterates `slot_scores` and renders position, player, starter/replacement metrics. |
| `frontend/src/components/hygiene/RosterHygienePanel.tsx` | Sectioned hygiene panel | ✓ VERIFIED | Renders Consolidate/Cut/Stash/Move to Taxi sections in order. |
| `frontend/src/components/hygiene/HygieneSuggestionRow.tsx` | Counterparty + package CTA for consolidation | ✓ VERIFIED | Shows manager label + `Evaluate This Package` link for consolidate rows. |
| `backend/src/fantasy/lineup/models.py` | Per-league taxi/eligibility/exception modeling | ⚠️ ORPHANED | Exists and wired for taxi fields, but manual exception modeling absent vs truth #5. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `lineup_engine.py` | `intelligence_service.py` | `self._lineup_engine.compute_all(...)` in league compute pipeline | WIRED | Lineup results computed and persisted during intelligence recompute. |
| `intelligence_service.py` | Direction classification | Outside-window contender fragility boost/reclassification | WIRED | Direction labels explicitly adjusted from lineup outcome. |
| `hygiene_engine.py` | `package_builder.py` | `PackageBuilder.build(...)` in consolidation path | WIRED | Trade-shape generation attempted and reasoning updated on fallback. |
| `frontend/src/api/queries.ts` | Backend lineup/hygiene/leagues routes | Query functions hitting `/intelligence/*` and `/leagues/*` endpoints | WIRED | Query options present and consumed by lineup/hygiene components. |
| `frontend/src/routes/league.$leagueId.tsx` | Phase 11 panels | Overview render block + downstream placement | WIRED | `TitleWindowPanel`, `LineupStrengthCard`, `RosterHygienePanel`, `TaxiIRSlotSummary`, `TaxiConfigForm` rendered in spec order. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `FS-02` | 11-01/02/03/04 | Contender reality / lineup strength modeling | ✗ BLOCKED | ID appears in plan frontmatter, roadmap, backlog; not defined in `.planning/REQUIREMENTS.md`. |
| `FS-04` | 11-01/02/03/04 | Roster management layer | ✗ BLOCKED | ID appears in plan frontmatter, roadmap, backlog; not defined in `.planning/REQUIREMENTS.md`. |

### Automated Verification

| Check | Status | Details |
| --- | --- | --- |
| Tests | ✓ | Targeted backend phase suite: 29/29 passing (`tests/lineup/*`, intelligence router/service integration set). |
| Build | ✓ | Frontend build/typecheck clean; backend package build clean; backend full pytest: 254/254 passing. |
| Type Safety | ✓ | Frontend `tsc --noEmit`: 0 errors. |
| Integration | ✓ | No package dependency or cross-package build breakpoints reported. |

Strict mode gate: no strict-mode regressions observed in executed typecheck/build checks.

### Anti-Patterns Found

No blocker anti-patterns found in verified phase artifacts. Guard-clause empty returns observed in engines are data-availability fallbacks, not placeholder stubs.

### Human Verification Required

### 1. Team screen visual QA

**Test:** Open a league overview with `user_roster_id` and verify panel styling/order/readability under real data.
**Expected:** Title window, lineup strength, hygiene, taxi/IR summary, and taxi config appear in intended order with consistent styling.
**Why human:** Visual hierarchy/UX quality cannot be fully validated by static analysis.

### 2. Taxi config interaction refresh behavior

**Test:** Change taxi config in UI and confirm lineup/hygiene interpretations refresh meaningfully for affected roster.
**Expected:** Save succeeds, query cache refreshes, downstream panels reflect updated eligibility context.
**Why human:** Requires runtime interaction and semantic validation of changed recommendations.

## Gaps Summary

Phase 11 is largely implemented and operational, with core backend/frontend wiring verified and automated checks passing. Two blockers remain for strict goal/traceability completion: (1) success criterion coverage is partial because manual exceptions are not modeled per league, and (2) requirement traceability is incomplete because `FS-02`/`FS-04` used by plans are absent from `.planning/REQUIREMENTS.md`.

---

_Verified: 2026-03-25T02:53:35Z_
_Verifier: Claude (gsd-verifier)_
