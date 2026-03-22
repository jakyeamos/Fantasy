# Phase 9: Portfolio & Retrospectives - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the cross-league portfolio exposure view, snapshot comparison tool, and backend retrospective grading system. Phase 9 delivers: a top-level Portfolio page showing player concentration, correlated team risk, and hedging recommendations; a per-league snapshot comparison tool (delta-forward, event-anchored); and a backend recalibration loop for direction labels and prospect tiers with a health indicator surface only. No grades UI — the value is model improvement, not a report card.

</domain>

<decisions>
## Implementation Decisions

### Navigation & entry points
- **D-01:** Phase 9 gets a top-level **Portfolio** nav section — separate from the main dashboard and league drill-ins; this is the only cross-league view in the app
- **D-02:** Snapshot comparison is **per-league** — launched from inside the league drill-in, not from the Portfolio page
- **D-03:** Retrospectives have **no dedicated route or view** — grades compute in the backend, a health indicator is the only surface ("Last recalibrated: [date]")

### Snapshot comparison (PORT-02)
- **D-04:** Snapshot selection uses **event-anchored labels**, not a raw date list — available anchors: trades (auto-labeled on execution), large roster changes (auto-labeled), start of season, end of season checkpoints
- **D-05:** View is **delta-forward** — one view showing what changed (direction arrows + magnitude), not a side-by-side two-column layout
- **D-06:** Player values show **movement direction + magnitude** (e.g., "WR1 ↓15 pts") — not raw historical numbers; players who left the roster since the snapshot still appear in the diff with a "traded/dropped" label
- **D-07:** Pick capital comparison uses the **Phase 6 computed capital score** — not a raw pick list diff; "Pick capital ↓22 pts" from Phase 6 dynamic valuation engine

### Portfolio exposure (PORT-03, PORT-04)
- **D-08:** Concentration flag (PORT-03) outputs a **recommendation hedge**, not just a warning — e.g., "Cooper is on all 3 rosters — consider trading him in your most contending league to reduce exposure"
- **D-09:** Portfolio risk scope (PORT-04) is **player cluster concentration only** — directional thesis clustering (all teams same direction label) and NFL schedule concentration are out of scope for v1
- **D-10:** Portfolio page shows a **full breakdown** — player × league exposure matrix; scannable but not collapsed by default
- **D-11:** **Correlated NFL team risk is flagged** — e.g., "You have CMC + Deebo + Aiyuk across 2 leagues — one 49ers collapse hits all three"; flagged alongside individual player concentration, not as a separate section

### Retrospectives (PORT-05, PORT-06)
- **D-12:** No grades UI — direction label grades (PORT-05) and prospect tier grades (PORT-06) are **backend-only**; grades feed model recalibration, results are not surfaced to the user
- **D-13:** Recalibration runs **once post-season** when NFL outcomes are resolved — not dynamically updated during the season
- **D-14:** Minimum surface: a **health indicator** on a relevant view (e.g., Portfolio page or settings) — "Last recalibrated: [date]"; no calibration percentages, no per-call breakdown

### Claude's Discretion
- Exact threshold for "large roster change" auto-labeling a snapshot anchor (e.g., 3+ players changed in one ingest)
- Health indicator placement (Portfolio page footer, settings panel, or dashboard)
- Exposure matrix row/column layout and sort order
- How correlated team risk clusters are detected (shared NFL team affiliation on player records)
- Snapshot diff ordering (sort by magnitude of change, or by field type)

</decisions>

<specifics>
## Specific Ideas

- The Portfolio page is the only place in the app with a true cross-league lens. Everything else is per-league. The exposure matrix should make multi-league risk scannable at a glance — the player is the row, the leagues are the columns, and the concentration flag + hedge rec appear inline.
- Event-anchored snapshot selection matters because "February 14th" is meaningless, but "after the Kelce trade" is instantly interpretable. Auto-labeling on trade execution gives users meaningful reference points without requiring manual annotation.
- The retrospectives health indicator is not "your model was right X% of the time" — it's just a signal that recalibration happened. The value is in future outputs being sharper, not in reviewing past calls.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Portfolio & retrospective requirements
- `.planning/REQUIREMENTS.md` §Portfolio & Memory — PORT-02 through PORT-06 (snapshot comparison, cross-league tracking, portfolio risk, direction grading, prospect grading)

### Snapshot foundation (Phase 3)
- `.planning/phases/03-core-dashboard/03-CONTEXT.md` — D-15 through D-19 (snapshot mechanism: auto-triggered after ingest, delta + monthly full, manual trigger, `league_snapshots` table, always full-portfolio); Phase 9 reads from this table, does not redefine snapshot writes
- `.planning/ROADMAP.md` §Phase 3 — PORT-01 success criteria (already built, Phase 9 depends on it)

### Pick capital engine (Phase 6)
- `.planning/phases/06-dynamic-pick-valuation/06-CONTEXT.md` — D-01 through D-08 (dynamic pick valuation engine, capital score output); Phase 9 snapshot comparison uses Phase 6 capital score for pick diff computation

### Prospect model outputs (Phase 8)
- `.planning/phases/08-historical-prospect-lab/08-CONTEXT.md` — D-01 through D-03 (hit/mediocre/bust buckets, outcome definitions); PORT-06 grading compares past tier assignments against these outcome labels
- `.planning/ROADMAP.md` §Phase 8 — `prospect_model_outputs` table (tier assignments Phase 9 grades against)

### Direction label definitions (Phase 2)
- `.planning/ROADMAP.md` §Phase 2 — 8 direction label definitions (true contender, fragile contender, etc.); PORT-05 grades past assignments of these labels against actual team outcomes

### UI patterns (existing)
- `.planning/phases/03-core-dashboard/03-CONTEXT.md` — D-01 through D-04 (dashboard layout, card pattern, drill-in routing); Portfolio page follows same card/grid conventions
- `.planning/phases/08-historical-prospect-lab/08-CONTEXT.md` — D-08 through D-09 (divergence direction + magnitude pattern, expandable sub-flags); snapshot diff direction + magnitude display follows same pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/SnapshotStatus.tsx`: Snapshot timestamp display — health indicator ("Last recalibrated") follows same pattern
- `frontend/src/components/RisersFallersList.tsx`: Direction + magnitude list pattern — snapshot diff rows reuse this visual (arrow + delta value + label)
- `frontend/src/components/LeagueCard.tsx`: Card pattern for league grid — Portfolio exposure matrix rows follow same card conventions
- `backend/src/fantasy/main.py`: FastAPI app factory — `/portfolio` router plugs in via `app.include_router()`
- `backend/src/fantasy/routers/deps.py`: DuckDB dependency injection — portfolio and snapshot comparison routers follow same pattern

### Established Patterns
- Engine package structure (Phase 6 `picks/` package: `constants.py`, `models.py`, `engine.py`, `repo.py`) — `portfolio/` package follows same layout
- Confidence/health label pattern (Phase 4 `MGR_MIN_TRADE_THRESHOLD`, Phase 8 low-confidence label) — recalibration health indicator follows same muted-text label approach
- DuckDB query pattern from `league_repo.py`, `pick_repo.py` — portfolio repo uses same connection approach
- shadcn `Badge` component for concentration flags — exposure level badges (1 league / 2 leagues / 3+ leagues) follow same usage as risk band badges in Phase 7

### Integration Points
- `league_snapshots` table (Phase 3): primary data source for snapshot comparison; Phase 9 reads delta and full snapshots keyed by `league_id + timestamp`
- `ingest_runs` table (Phase 1): trade and roster-change events — used to auto-label snapshot anchors on event detection
- Phase 6 pick valuation engine: `capital_score` output used for pick capital comparison in snapshot diff
- Phase 8 `prospect_model_outputs` table: tier assignments at time of prediction — PORT-06 grading reads these to compare against resolved NFL outcomes
- Phase 2 `team_directions` table: direction label history — PORT-05 grading reads past direction assignments to compare against actual season outcomes
- New tables likely needed: `portfolio_exposure_cache` (cross-league player ownership matrix), `retrospective_runs` (recalibration run timestamps and metadata)

</code_context>

<deferred>
## Deferred Ideas

- Directional thesis clustering ("all 3 teams are rebuild — if the draft class disappoints, all 3 lose") — PORT-04 scope is player cluster only in v1; thesis concentration is backlog
- NFL schedule concentration as a distinct portfolio risk signal (separate from correlated team exposure) — out of scope for v1
- Grades UI for retrospectives (calibration percentages, per-call breakdown, direction model accuracy report) — backend recalibration only in v1; if users want to audit model accuracy in v2, expose the grades then
- Suggested target round on snapshot comparison ("you could have sold WR1 here — value peaked at this snapshot") — descriptive diff only, no prescriptive action layer
- Cross-league rookie board comparison ("your 1.01 in League A is worth more than your 1.04 in League B") — deferred; portfolio scope is roster exposure, not pick arbitrage across leagues

</deferred>

---

*Phase: 09-portfolio-retrospectives*
*Context gathered: 2026-03-22*
