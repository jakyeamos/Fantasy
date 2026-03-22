# Phase 7: Rookie Board & Draft Room - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the format-aware rookie board and draft room view. The rookie board displays the current draft class with tiers, archetype labels, and risk bands adjusted for the active league's scoring format. The draft room answers three questions a manager needs on the clock: best player in abstract, best relative to this league's draft tendencies, and whether trading the pick is the superior play. This phase wires in the Phase 6 `class_strength` hook with actual class evaluation data.

</domain>

<decisions>
## Implementation Decisions

### Rookie board layout (PICK-04)
- **D-01:** Tiered card grid — players grouped in visual tier blocks, not a flat ranked list
- **D-02:** Labeled tier dividers between blocks (e.g., "Tier 1 — Elite", "Tier 2 — Strong Day 2") — explicit break lines, not per-row indicators
- **D-03:** Always visible inline on each card: name, position, archetype label — no expand or hover required for these three fields
- **D-04:** Risk band rendered as both a text label ("Low" / "Moderate" / "High") and a color-coded element (badge color or left border tint) — not one or the other

### Roster-fit overlay (PICK-05)
- **D-05:** PICK-05 roster-fit filtered board is **descoped** — dynasty strategy is value accumulation, not positional need filling; a heavy roster-fit rerank would push toward suboptimal positional thinking in flex formats
- **D-06:** The team/draft-slot dropdown (if present) is repurposed to **highlight players likely available at a given pick slot**, not to apply roster-fit weighting

### Draft room view (PICK-06)
- **D-07:** "Best for this roster" question **dropped** from draft room — same rationale as D-05; reduces to 3 questions: (1) best in abstract, (2) best relative to this league's draft tendencies, (3) trade vs. use the pick
- **D-08:** Dedicated route (`/draft-room`) — user selects league and pick slot on entry; not a modal or panel launched from the board
- **D-09:** Trade recommendation is a **direct verdict** with one-line reasoning ("Trade it — your 1.04 carries more value than any available prospect here"), not a side-by-side comparison view
- **D-10:** League draft tendency warnings surface **both**: positional run warnings ("WRs always go early in this league — don't wait") and value gap alerts ("Player X is being drafted 3 spots earlier than his value")

### Entry points and navigation
- **D-11:** Rookie board lives inside the **league drill-in** — accessed per league, not top-level nav; format recalculates for each league's scoring rules
- **D-12:** Draft room is reached from the **league drill-in** — not launched from the rookie board itself
- **D-13:** Phase 6 "Use on the clock" timing rec is a **label only** — no navigation link into the draft room
- **D-14:** Each league gets its **own board instance** — tiers, risk bands, and archetype labels are recalculated per-league scoring format; no shared cross-league board view

### Claude's Discretion
- Exact tier names and count (how many tiers, what they're called)
- Which color tokens map to which risk bands (within existing shadcn CSS variable set)
- How archetype labels are generated and what the label vocabulary is
- How "available at pick slot" is estimated for the draft-slot dropdown
- How league draft tendencies are derived (positional draft frequency, ADP delta vs. system value)
- Pick slot selector UX on draft room entry (input, dropdown, or stepper)

</decisions>

<specifics>
## Specific Ideas

- The rookie board's primary value is opinionated tiers — the tier divider label should be prominent enough that you scan by tier, not by individual rank number. Rank numbers within a tier are secondary.
- The draft room's trade verdict is the most actionable single output. "Trade it" with no reasoning is useless — the one-line reason is what drives the decision, same pattern as the Phase 6 timing rec reasoning.
- League draft tendency warnings are most valuable early in the draft when you're deciding whether to reach vs. wait. A positional run warning ("WRs go earlier here") should surface before you're already in the run, not after.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pick & Rookie Engine requirements
- `.planning/REQUIREMENTS.md` §Pick & Rookie Engine — PICK-04 (format-aware rookie board), PICK-05 (descoped — see D-05), PICK-06 (draft room, reduced to 3 questions per D-07)
- `.planning/ROADMAP.md` §Phase 7 — goal, success criteria, phase dependencies

### Phase 6 integration (class strength hook)
- `.planning/phases/06-dynamic-pick-valuation/06-CONTEXT.md` — D-01/D-02 (class_strength is a neutral placeholder in Phase 6; Phase 7 provides the real value), D-05/D-06 (timing rec states and display), code_context §Integration Points (class_strength hook interface spec)

### UI patterns (for frontend consistency)
- `.planning/phases/03-core-dashboard/03-UI-SPEC.md` — spacing scale, typography, color tokens
- `.planning/phases/06-dynamic-pick-valuation/06-UI-SPEC.md` — timing badge display, pick display patterns — Phase 7 board and draft room use the same visual language

### Existing routes and navigation patterns
- `frontend/src/routes/league.$leagueId.tsx` — league drill-in route; Phase 7 adds rookie board as a nested route here
- `frontend/src/routes/league.$leagueId.managers.tsx` — pattern for nested league routes to follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/trade/AssetChip.tsx`: Pick identity display pattern (owner, year, round) — draft room pick slot selection can reuse the same label logic
- `frontend/src/components/trade/DimensionScoreRow.tsx`: Inline reasoning string pattern — draft room verdicts follow same treatment (label + one-line reasoning)
- `frontend/src/components/trade/StrategicDistinctionBanner.tsx`: Direct verdict banner pattern — draft room "Trade it / Use it" verdict reuses this visual approach
- `backend/src/fantasy/main.py`: FastAPI app factory — `/rookie-board` and `/draft-room` routers plug in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: DuckDB dependency injection — new routers follow same pattern

### Established Patterns
- Nested league routes: `league.$leagueId.managers.tsx` → Phase 7 adds `league.$leagueId.rookie-board.tsx` following same pattern
- shadcn `Badge` with variant for colored labels — already used in AssetChip; risk band badge follows same usage
- `trades.tsx` dedicated route pattern — `/draft-room` follows same standalone route approach
- Inline reasoning strings (12px / `text-muted-foreground`) established in Phase 6 UI-SPEC — draft room trade verdict reasoning follows this token

### Installed shadcn Components (do not reinstall)
- Phase 3: card, badge, button, separator, skeleton
- Phase 4: tabs, table, alert
- Phase 5: sheet, input, command, popover, scroll-area

### Integration Points
- Phase 6 `pick_engine.py`: `class_strength` parameter — Phase 7 replaces the neutral `0.0` placeholder with actual class evaluation output
- `picks` table (Phase 1 INGEST-04): pick ownership per league per team — draft room pick slot selection reads from here
- `league_draft_tendencies` (new table): positional draft frequency and ADP delta per league — new Phase 7 table, feeds draft room tendency warnings
- League drill-in route (`league.$leagueId.tsx`): needs "Rookie Board" and "Draft Room" navigation affordances added

</code_context>

<deferred>
## Deferred Ideas

- Roster-fit filtered board (PICK-05) — descoped; user prefers pure value accumulation strategy over positional need filtering in dynasty flex formats
- "Best for this roster" as a draft room question — same rationale; dropped from PICK-06 scope
- Historical rookie class outcome tracking (did Tier 1 picks hit?) — Phase 8/9 retrospective feature
- Cross-league rookie board comparison (same player, different format adjustments side by side) — future phase

</deferred>

---

*Phase: 07-rookie-board-draft-room*
*Context gathered: 2026-03-22*
