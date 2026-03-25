# Phase 12: Manager Rookie & Pick Profiles - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend manager dossiers into rookie-draft and pick-market behavior. Mine startup draft selections and pick-trade transaction history to produce per-manager positional preferences, archetype tendencies, and pick-premium scores. Surface these in the dossier UI and feed them into package builder, reroute suggestions, and draft-room warnings.

Trade evaluation (Phase 5), package builder (Phase 5), reroute engine (Phase 5), and draft room (Phase 7) are consumed and extended here — not rebuilt. The manager profiling engine (Phase 4) is extended, not replaced.

</domain>

<decisions>
## Implementation Decisions

### Dossier layout
- **D-01:** Hybrid layout — Overview tab gains a compact "Rookie & Pick Market" summary card (positional tendency + dominant archetype + pick-premium indicator); a new 4th tab "Draft & Picks" holds the full breakdown (per-season draft history, archetype hit patterns, pick-premium score detail)
- **D-02:** The "Draft & Picks" tab is **hidden entirely** when evidence is below the low-confidence threshold — no placeholder, no empty state; startup draft signals are still computed and fed into the Overview card and integration surfaces regardless
- **D-03:** Pick-premium score lives inside the "Draft & Picks" tab detail, not in the dossier header alongside the exploitability score

### Managers list
- **D-04:** The managers list row gains a "picks buyer" indicator badge (or equivalent) when a manager has a measurable pick-premium score with sufficient evidence; visible at the quick-scan level alongside the exploitability score and top pitch angle

### Draft-room warnings
- **D-05:** Manager-level draft tendency warnings (e.g., "Manager X in this league consistently targets WRs rounds 1-2") are a **separate surface** from the dossier — surfaced in the draft room view alongside existing positional run and value gap warnings
- **D-06:** Manager tendency warnings are formatted using the same `TendencyWarning` shape as existing warnings (same `warning_type` enum extension, same display treatment)

### Data sourcing
- **D-07:** Pick-trade behavior from transaction history (picks appearing on either side of a trade) is the **primary signal** for pick-premium scoring; draft selections (startup + future rookie drafts) are supplementary
- **D-08:** Both connected leagues are new in 2026 — only startup draft data exists; no historical rookie draft records available yet. This is the expected data state and does not block the phase.
- **D-09:** Startup draft selections are **valid signal** for positional preference and archetype tendency analysis. They are **not valid** for early-vs-late slot aggression analysis (slot numbers in a startup draft do not carry the same meaning as in a rookie-only draft)
- **D-10:** Neither connected league is a keeper league — no keeper handling required
- **D-11:** Historical draft pick ingestion is a **separate on-demand step**, not wired into the main ingest flow (drafted picks change infrequently; slow fetch should not block a standard ingest run)

### Signal design
- **D-12:** Pick-premium scoring reuses and extends the existing profiling engine's value-delta logic — a `RookiePickProfileEngine` (or equivalent extension) computes how much market value a manager gives up to acquire picks vs. how readily they sell picks in transactions
- **D-13:** Positional preference from draft selections is computed **relative to the rest of the league** in that draft (not against ADP baselines) — did this manager take WRs earlier than everyone else in this room?
- **D-14:** Draft pick selections are mapped to **Phase 7 archetype label vocabulary** retroactively (ceiling bet, safe floor, etc.) to keep archetype language consistent across surfaces

### Integration surfaces
- **D-15:** Package builder uses **tiered logic** based on evidence level:
  - Sufficient evidence → change package *structure* (e.g., include a pick in the offer)
  - Thin evidence → change reasoning *text* only (no structural change)
- **D-16:** New reroute type: **"picks buyer"** — surfaces when counterparty has a measurable pick-premium score; distinct from the existing pick-based reroute (which is about value equivalence, not manager behavior)
- **D-17:** Low-confidence pick/rookie signals are **silently omitted** from all integration surfaces (package builder, reroutes, draft room) — no LOW CONFIDENCE qualifier shown on trade or draft surfaces (contrast with Phase 4 dossier which shows an explicit banner)

### Evidence thresholds
- **D-18:** The low-confidence suppression threshold for rookie/pick profiles is a named constant (e.g., `MIN_ROOKIE_PICK_EVIDENCE`) — exact value to be determined during planning/research, but the threshold applies to **display of the 4th tab only**; signals are always computed and always fed into integration surfaces (silently omitted if thin per D-17)

### Claude's Discretion
- Exact value of `MIN_ROOKIE_PICK_EVIDENCE` constant
- Whether `RookiePickProfileEngine` is a subclass of `ProfilingEngine` or a standalone engine that calls `ProfilingRepo`
- Specific new `warning_type` enum value for manager tendency warnings
- Exact badge label for the managers list "picks buyer" indicator
- Which Phase 7 archetype labels map to which draft pick attributes (research should define this mapping)
- Alembic migration number (currently 015 is next after 014)

</decisions>

<specifics>
## Specific Ideas

- Evidence sparsity is the core constraint for this phase. With 1 draft/year and ~4 picks per manager per draft, even 5 seasons = ~20 selections. Most managers will trigger the evidence floor for the draft tab. The phase should be designed with this as the *expected* state, not an edge case.
- Pick-trade behavior from transactions is rich and grows every time a trade happens. This is where the real signal lives right now. The draft selection layer will compound in value as leagues age.
- The "picks buyer" reroute type is most valuable when the counterparty is bidding up picks in trades — a manager who consistently overpays for early firsts is a natural target for pick-for-player deals.
- Startup draft positional preference is genuinely informative — a manager who spent 6 of their first 12 picks on WRs in the startup has a documented pattern, even if it's only one data point.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12 requirements
- `.planning/REQUIREMENTS.md` — no standalone FS-06 entry; full task breakdown in backlog
- `.planning/FANTASY-BACKLOG.md` §FS-06 — "Manager Rookie / Pick Market Profiles" task breakdown (mine selections, score pick-premium, feed tendencies into package builder / reroute / draft room, add low-confidence suppression)
- `.planning/ROADMAP.md` §Phase 12 — goal, success criteria, dependency on Phase 11

### Phase 4 profiling (extending, not replacing)
- `.planning/phases/04-manager-profiling/04-CONTEXT.md` — D-09 through D-17: exploitation type classification, evidence floor pattern (`MIN_TRADE_EVIDENCE_THRESHOLD = 10`), LOW CONFIDENCE banner design, pitch angle structure
- `backend/src/fantasy/profiling/profiling_engine.py` — value-delta logic to reuse for pick-premium scoring; trade history query pattern
- `backend/src/fantasy/profiling/models.py` — `ManagerProfile`, `ManagerSummary` models to extend
- `backend/src/fantasy/routers/profiling.py` — existing endpoints; Phase 12 adds new endpoints without breaking existing ones

### Phase 7 archetype labels (mapping target)
- `.planning/phases/07-rookie-board-draft-room/07-CONTEXT.md` — D-01 through D-10: archetype label vocabulary, tier structure, draft tendency warning design
- `backend/src/fantasy/rookie/models.py` — `RookiePlayer.archetype_label`, `TendencyWarning` model (Phase 12 extends `warning_type` enum)
- `backend/src/fantasy/rookie/rookie_engine.py` — existing archetype label generation logic; Phase 12 maps draft picks to these labels retroactively

### Phase 5 integration points (package builder + reroutes)
- `backend/src/fantasy/trade/package_builder.py` — existing manager profile read via `TradeRepo.get_manager_profile()`; Phase 12 adds pick-premium to the profile data it reads
- `backend/src/fantasy/trade/reroute_engine.py` — existing reroute types; Phase 12 adds "picks buyer" reroute type
- `backend/src/fantasy/trade/models.py` — `PackageBuilderResult`, reroute models

### Sleeper ingestion (new endpoint needed)
- `backend/src/fantasy/ingestion/sleeper_client.py` — needs `fetch_draft_picks(draft_id)` added: `GET /draft/{draft_id}/picks`
- `backend/src/fantasy/ingestion/sleeper_mapper.py` — existing `map_draft_slots()` for context; new mapper method needed for draft pick selections
- `backend/src/fantasy/ingestion/ingest_service.py` — on-demand draft pick fetch wired as a separate step (not main ingest flow per D-11)

### Frontend dossier (extending tabs)
- `frontend/src/routes/league.$leagueId.managers.$managerId.tsx` — existing 3-tab dossier; Phase 12 adds 4th tab (conditionally rendered)
- `frontend/src/components/DossierOverviewTab.tsx` — gains "Rookie & Pick Market" summary card
- `frontend/src/components/ManagerListRow.tsx` — gains "picks buyer" badge
- `frontend/src/routes/draft-room.tsx` — gains manager tendency warning type

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/src/fantasy/profiling/profiling_engine.py`: Value-delta computation logic — reuse for pick-premium scoring without duplication
- `backend/src/fantasy/rookie/models.py` `TendencyWarning`: Extend `warning_type` Literal to include manager-level tendency type; no new model needed for draft room warnings
- `backend/src/fantasy/trade/package_builder.py`: Already reads `manager_profile` via `TradeRepo.get_manager_profile()` — pick-premium score flows in via this same read path
- `frontend/src/components/DossierOverviewTab.tsx`: Card pattern established; "Rookie & Pick Market" card follows same `<Card>` / `<CardContent>` structure

### Established Patterns
- Evidence floor constant pattern from Phase 4: `MIN_TRADE_EVIDENCE_THRESHOLD = 10` in `profiling/constants.py` — Phase 12 adds `MIN_ROOKIE_PICK_EVIDENCE` in same file or new `rookie_pick/constants.py`
- Conditional tab rendering: dossier already conditionally renders LOW CONFIDENCE banner; tab-level conditional follows same guard pattern
- DuckDB upsert pattern from `profiling_repo.py` — new `RookiePickRepo` (or extension) follows same connection pattern
- `app.include_router()` in `main.py` — any new Phase 12 router (if needed) wires in same way

### Integration Points
- `trades` table (Phase 1): primary data source for pick-trade signal — picks appearing in `draft_picks` field of transaction records
- `draft_slots` table (Phase 10/11 migration 011): has `slot_to_roster_id` mapping — startup draft pick-to-roster attribution reads from here
- `manager_profiles` table (Phase 4): the Phase 12 profile extension either adds columns to this table or creates a linked `manager_rookie_pick_profiles` table
- `league_draft_tendencies` table (Phase 7 migration 010): manager tendency warnings in draft room join against this; Phase 12 may extend it with per-manager rows

</code_context>

<deferred>
## Deferred Ideas

- Year-over-year rookie draft behavior comparison (did manager's archetype preference shift after a bust?) — requires multiple rookie drafts; viable in Phase 9 retrospectives
- Cross-league pick-premium comparison (does this manager behave differently across leagues?) — Phase 16 portfolio thesis expansion
- "Picks seller" profile as a distinct type from "picks buyer" — directionally interesting but requires clean signal separation; defer to Phase 13+ if data supports it
- Startup draft slot aggression analysis (did they reach or get value?) — requires calibrated ADP baseline for startup context; different problem than rookie-only slot analysis; not in scope

</deferred>

---

*Phase: 12-manager-rookie-pick-profiles*
*Context gathered: 2026-03-25*
