---
phase: 12
slug: manager-rookie-pick-profiles
status: complete
researched: 2026-03-25
---

# Phase 12 Research: Manager Rookie & Pick Profiles

---

## User Constraints

### Locked Decisions (planner MUST honor these verbatim)

**Dossier layout**
- D-01: Hybrid layout — Overview tab gains a compact "Rookie & Pick Market" summary card (positional tendency + dominant archetype + pick-premium indicator); a new 4th tab "Draft & Picks" holds the full breakdown (per-season draft history, archetype hit patterns, pick-premium score detail)
- D-02: The "Draft & Picks" tab is hidden entirely when evidence is below the low-confidence threshold — no placeholder, no empty state; startup draft signals are still computed and fed into the Overview card and integration surfaces regardless
- D-03: Pick-premium score lives inside the "Draft & Picks" tab detail, not in the dossier header alongside the exploitability score

**Managers list**
- D-04: The managers list row gains a "picks buyer" indicator badge (or equivalent) when a manager has a measurable pick-premium score with sufficient evidence; visible at the quick-scan level alongside the exploitability score and top pitch angle

**Draft-room warnings**
- D-05: Manager-level draft tendency warnings are a separate surface from the dossier — surfaced in the draft room view alongside existing positional run and value gap warnings
- D-06: Manager tendency warnings use the same `TendencyWarning` shape as existing warnings (same `warning_type` enum extension, same display treatment)

**Data sourcing**
- D-07: Pick-trade behavior from transaction history (picks appearing on either side of a trade) is the primary signal for pick-premium scoring; draft selections (startup + future rookie drafts) are supplementary
- D-08: Both connected leagues are new in 2026 — only startup draft data exists; no historical rookie draft records available yet. This is the expected data state and does not block the phase.
- D-09: Startup draft selections are valid signal for positional preference and archetype tendency analysis. They are NOT valid for early-vs-late slot aggression analysis.
- D-10: Neither connected league is a keeper league — no keeper handling required
- D-11: Historical draft pick ingestion is a separate on-demand step, not wired into the main ingest flow

**Signal design**
- D-12: Pick-premium scoring reuses and extends the existing profiling engine's value-delta logic — a `RookiePickProfileEngine` (or equivalent extension) computes how much market value a manager gives up to acquire picks vs. how readily they sell picks in transactions
- D-13: Positional preference from draft selections is computed relative to the rest of the league in that draft (not against ADP baselines)
- D-14: Draft pick selections are mapped to Phase 7 archetype label vocabulary retroactively

**Integration surfaces**
- D-15: Package builder uses tiered logic based on evidence level: sufficient evidence → change package structure; thin evidence → change reasoning text only
- D-16: New reroute type: "picks buyer" — surfaces when counterparty has a measurable pick-premium score; distinct from existing pick-based reroute
- D-17: Low-confidence pick/rookie signals are silently omitted from all integration surfaces — no LOW CONFIDENCE qualifier shown on trade or draft surfaces

**Evidence thresholds**
- D-18: `MIN_ROOKIE_PICK_EVIDENCE` is a named constant — exact value TBD during planning; threshold applies to display of 4th tab only; signals always computed

### Claude's Discretion
- Exact value of `MIN_ROOKIE_PICK_EVIDENCE` constant
- Whether `RookiePickProfileEngine` is a subclass of `ProfilingEngine` or a standalone engine that calls `ProfilingRepo`
- Specific new `warning_type` enum value for manager tendency warnings
- Exact badge label for the managers list "picks buyer" indicator
- Which Phase 7 archetype labels map to which draft pick attributes
- Alembic migration number (015 is next after 014)

### Deferred Ideas (out of scope — do not plan)
- Year-over-year rookie draft behavior comparison (requires multiple rookie drafts)
- Cross-league pick-premium comparison (Phase 16)
- "Picks seller" profile as a distinct type (Phase 13+)
- Startup draft slot aggression analysis (requires calibrated ADP baseline)

---

## Standard Stack

### Core (confirmed from codebase inspection)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | All DB queries, upserts, analytical joins | Established project-wide; 10-17x faster for analytical patterns |
| pydantic | v2 | Domain models, validation | All existing models use Pydantic v2 BaseModel with ConfigDict |
| fastapi | current | Router endpoints | All existing routers use FastAPI |
| httpx + tenacity | current | Sleeper API client with retry | Pattern established in `SleeperClient` |
| polars | current | Bulk ingestion transforms | Used in `IngestService` |
| React 19 + TanStack Query | current | Frontend state + data fetching | Project standard |
| shadcn-compatible primitives | custom | UI components | All existing: Card, Badge, Button, Skeleton, Separator |

**Confidence:** HIGH — verified by direct code inspection of existing engine, repo, router, and component files.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| statistics.mean | stdlib | Average pick value deltas | Already used in profiling_engine.py |
| collections.Counter | stdlib | Positional frequency counts | Already used in profiling_engine.py |
| collections.defaultdict | stdlib | Per-manager draft selection bucketing | Already used in profiling_engine.py |
| json | stdlib | JSON column serialization for DuckDB VARCHAR columns | Established pattern throughout |

### No New Dependencies Required

Phase 12 does not require any new Python packages or frontend npm packages. All capabilities are achievable with the existing stack. Confidence: HIGH.

---

## Architecture Patterns

### Recommended File Structure

```
backend/src/fantasy/
├── profiling/
│   ├── constants.py              # Add MIN_ROOKIE_PICK_EVIDENCE here
│   ├── models.py                 # Add RookiePickProfile model
│   ├── profiling_engine.py       # Unchanged
│   └── profiling_repo.py         # Unchanged
├── rookie_pick/                  # New package
│   ├── __init__.py
│   ├── constants.py              # PICK_PREMIUM_THRESHOLD, archetype mapping table
│   ├── models.py                 # RookiePickProfile Pydantic model
│   ├── rookie_pick_engine.py     # RookiePickProfileEngine
│   └── rookie_pick_repo.py       # DuckDB read/write for draft_pick_selections + rookie_pick_profiles
├── ingestion/
│   ├── sleeper_client.py         # Add fetch_draft_picks(draft_id)
│   └── sleeper_mapper.py         # Add map_draft_pick_selections()
├── routers/
│   └── profiling.py              # Add new endpoints (GET /profiles/{rosterId}/rookie-pick)
backend/alembic/versions/
└── 015_rookie_pick_profiles.py   # New migration

frontend/src/
├── components/
│   ├── DossierOverviewTab.tsx    # Add RookiePickMarketCard
│   ├── ManagerListRow.tsx        # Add "Picks Buyer" badge
│   ├── DossierDraftPicksTab.tsx  # New: full tab component
│   └── RookiePickMarketCard.tsx  # New: Overview summary card
├── routes/
│   └── league.$leagueId.managers.$managerId.tsx  # Add 4th tab
```

### Pattern 1: Standalone Engine Calling ProfilingRepo (Recommended)

**What:** `RookiePickProfileEngine` is a standalone engine (not a subclass of `ProfilingEngine`) that accepts a `duckdb.DuckDBPyConnection` and calls `ProfilingRepo` only to read existing trade data. It has its own `RookiePickRepo` for storing its output.

**Why:** The existing `ProfilingEngine` is a self-contained compute unit with its own `compute_profile` method. Subclassing creates brittle coupling — any change to `ProfilingEngine.__init__` or private methods would silently break the subclass. A standalone engine follows the established pattern of `RookieEngine` (Phase 7), which is also standalone despite operating in the same domain.

**Confidence:** HIGH — directly validated by reading `profiling_engine.py` and `rookie_engine.py` side by side.

```python
# Source: pattern from backend/src/fantasy/rookie/rookie_engine.py
class RookiePickProfileEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = RookiePickRepo(conn)

    def compute_profile(self, league_id: str, roster_id: int) -> RookiePickProfile:
        pick_trades = self._load_pick_trades(league_id, roster_id)
        draft_selections = self._repo.get_draft_selections(league_id, roster_id)
        pick_premium_score = self._compute_pick_premium(pick_trades)
        positional_tendency = self._compute_positional_tendency(draft_selections, league_id)
        dominant_archetype = self._map_to_archetype(draft_selections)
        evidence_count = len(pick_trades) + len(draft_selections)
        show_tab = evidence_count >= MIN_ROOKIE_PICK_EVIDENCE
        return RookiePickProfile(...)
```

### Pattern 2: Pick-Premium Scoring via Value-Delta Reuse

**What:** Reuse `ProfilingEngine._compute_value_delta()` and `ProfilingEngine._parse_trade_sides()` logic directly. Extract pick-specific trades from the `transactions` table where `draft_picks` is non-empty.

**Key insight from code inspection:** `profiling_engine.py` lines 103–113 already parse `draft_picks` from each transaction into `received_pick_rounds` and `sent_pick_rounds`. The `PICK_VALUE_NORMALIZED` constant in `profiling/constants.py` maps round → normalized value: `{1: 0.70, 2: 0.45, 3: 0.25, 4: 0.10}`.

Pick-premium score measures: for trades where picks appear on either side, what is the manager's average value delta? A consistently negative delta when acquiring picks (overpaying) signals high pick-premium. A consistently positive delta when trading away picks (underselling) is the inverse signal.

```python
# Reuse from backend/src/fantasy/profiling/constants.py
PICK_VALUE_NORMALIZED = {1: 0.70, 2: 0.45, 3: 0.25, 4: 0.10}

def _compute_pick_premium(self, pick_trades: list[dict]) -> float:
    # Filter trades where manager acquired picks
    acquisition_deltas = [
        self._compute_value_delta(received, sent, received_picks, sent_picks, adp_map)
        for t in pick_trades
        for received, sent, received_picks, sent_picks in [self._parse_trade_sides(t, roster_id)]
        if received_picks  # only trades where picks were received
    ]
    if not acquisition_deltas:
        return 0.0
    # Negative avg_delta = overpaid to acquire picks = high pick-premium
    return round(-mean(acquisition_deltas), 3)
```

**Confidence:** HIGH — PICK_VALUE_NORMALIZED and value-delta logic verified in `profiling/constants.py` and `profiling_engine.py`.

### Pattern 3: Positional Tendency (League-Relative, D-13)

**What:** For startup draft data, count each manager's position selections weighted by early vs. late draft slot within the draft. Compare each manager's positional share against the league average positional share in that draft.

**Why league-relative (not ADP):** D-13 is explicit. The question is not "did they reach for a WR?" but "did they take WRs proportionally earlier than everyone else in this room?" This avoids needing an external ADP baseline and is more meaningful in startup drafts where overall ADP doesn't directly apply.

```python
# Compute positional share per manager, subtract league avg share
def _compute_positional_tendency(
    self, selections: list[dict], all_league_selections: list[dict]
) -> dict[str, float]:
    league_position_share = _position_share(all_league_selections)
    manager_position_share = _position_share(selections)
    return {
        pos: round(manager_position_share.get(pos, 0.0) - league_position_share.get(pos, 0.0), 3)
        for pos in {"QB", "RB", "WR", "TE"}
    }
```

**Confidence:** HIGH (pattern design is sound given D-13 constraint; no external dependency needed).

### Pattern 4: Archetype Mapping from Phase 7 Vocabulary (D-14)

**What:** Map draft pick selections to Phase 7 archetype labels retroactively. Use the same `_assign_archetype()` logic from `rookie_engine.py` if the selected player exists in the `players` table with metadata. Fall back to position-based dominant archetype labels when metadata is sparse.

**Phase 7 Archetype Vocabulary (verified from `rookie_engine.py` lines 230–273):**

| Position | Labels Available |
|----------|-----------------|
| WR | Slot Receiver, Deep Threat, Contested Catch WR, Route Runner, Possession WR |
| RB | Receiving Back, Power Back, Workhorse, Early Down Back |
| QB | Dual Threat QB, Scrambler, Pro Style QB, Pocket Passer |
| TE | Move TE, H-Back, Receiving TE, Inline Blocker |

**Mapping approach for draft selections:** When a manager consistently targets one archetype (e.g., 3 of 5 WR picks are "Deep Threat"), that is the `dominant_archetype`. Minimum 2 selections of the same archetype to register a pattern.

**Confidence:** HIGH — archetype assignment logic fully read in `rookie_engine.py`.

### Pattern 5: New `warning_type` Enum Extension (D-06)

**What:** The existing `WarningType` Literal in `backend/src/fantasy/rookie/models.py` line 10 is:
```python
WarningType = Literal["positional_run", "value_gap"]
```

Phase 12 extends this to:
```python
WarningType = Literal["positional_run", "value_gap", "manager_tendency"]
```

Manager tendency warnings use `warning_type="manager_tendency"`, `title="[Manager Name] targets [Position] early"`, `description="[Manager] has targeted [Position] in [N] of [N] draft selections in this league."`.

**Confidence:** HIGH — `TendencyWarning` model and `WarningType` Literal verified in `rookie/models.py`.

### Pattern 6: Package Builder Integration (D-15)

**What:** `PackageBuilder.build()` already reads `manager_profile` via `self._repo.get_manager_profile()` (lines 26–34 in `package_builder.py`). Phase 12 adds `pick_premium_score` to the profile data returned by that read path.

Tiered logic:
- Sufficient evidence (`pick_premium_score` is non-None and evidence >= `MIN_ROOKIE_PICK_EVIDENCE`): add a pick to `aggressive_sends` list if not already present, or keep existing structure but promote any pick already in the offer
- Thin evidence: change `aggressive_reasoning` text only to mention the manager's pick interest, no structural change to `send_assets`

**Confidence:** HIGH — `package_builder.py` fully read; integration point is lines 44–50.

### Pattern 7: "Picks Buyer" Reroute Type (D-16)

**What:** Extend `RerouteResult.reroute_type` Literal in `trade/models.py` line 47:
```python
# Current:
reroute_type: Literal["better_target", "better_package"]
# Phase 12:
reroute_type: Literal["better_target", "better_package", "picks_buyer"]
```

The "picks buyer" reroute fires when: counterparty has a `pick_premium_score` above threshold AND the current trade does not include picks on the user's receive side. Headline: "Consider including a pick — [Manager] consistently pays a premium for draft capital."

**Confidence:** HIGH — `RerouteResult` model verified in `trade/models.py`.

### Pattern 8: DuckDB Upsert (Established Pattern)

All new tables follow the exact pattern from `profiling_repo.py`: `SELECT id` first to check existence, then `INSERT ... ON CONFLICT ... DO UPDATE SET`. Integer primary key via `COALESCE(MAX(id), 0) + 1`. JSON blobs serialized with `json.dumps(..., separators=(",", ":"))`.

**Confidence:** HIGH — verified in `profiling_repo.py` lines 24–73.

### Pattern 9: Schema Triple-Write (Critical — Existing Constraint)

**From STATE.md:** Any new table must be added in three places or it will fail silently:
1. Alembic migration (015)
2. `_SCHEMA_COMPAT_TABLES` dict in `startup_tasks.py`
3. `conftest.py` test schema bootstrap

**Verified from `startup_tasks.py`:** `_SCHEMA_COMPAT_TABLES` currently covers: `pick_values`, `rookie_board_cache`, `league_draft_tendencies`, `draft_slots`, `league_draft_order_rules`, `league_taxi_configs`, `lineup_scores`, `hygiene_suggestions`, `retrospective_runs`. Phase 12 adds at minimum `draft_pick_selections` and `manager_rookie_pick_profiles` to all three locations.

**Confidence:** HIGH — direct code inspection of `startup_tasks.py` lines 18–143.

---

## Database Design

### New Tables (migration 015)

**`draft_pick_selections`** — stores per-manager startup and rookie draft picks
```sql
CREATE TABLE IF NOT EXISTS draft_pick_selections (
    id              INTEGER PRIMARY KEY,
    league_id       VARCHAR NOT NULL,
    draft_id        VARCHAR NOT NULL,
    roster_id       INTEGER NOT NULL,
    player_id       VARCHAR NOT NULL,
    pick_slot       INTEGER NOT NULL,
    round_number    INTEGER NOT NULL,
    season          INTEGER NOT NULL,
    draft_type      VARCHAR NOT NULL,  -- 'startup' | 'rookie'
    position        VARCHAR,
    archetype_label VARCHAR,           -- mapped from Phase 7 vocabulary
    ingested_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (league_id, draft_id, roster_id, player_id)
)
```

**`manager_rookie_pick_profiles`** — computed rookie/pick market profile per manager
```sql
CREATE TABLE IF NOT EXISTS manager_rookie_pick_profiles (
    id                      INTEGER PRIMARY KEY,
    league_id               VARCHAR NOT NULL,
    roster_id               INTEGER NOT NULL,
    computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pick_premium_score      FLOAT,
    pick_trade_evidence     INTEGER NOT NULL DEFAULT 0,
    draft_selection_count   INTEGER NOT NULL DEFAULT 0,
    positional_tendency_json VARCHAR NOT NULL DEFAULT '{}',
    dominant_archetype      VARCHAR,
    archetype_pattern_json  VARCHAR NOT NULL DEFAULT '{}',
    show_draft_picks_tab    BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (league_id, roster_id)
)
```

**Approach decision:** A separate linked table (`manager_rookie_pick_profiles`) rather than adding columns to `manager_profiles`. Rationale: `manager_profiles` is already upserted by `ProfilingEngine` — adding nullable columns to it would require coordinating two engines writing to the same row, creating a race condition risk. A separate table with `(league_id, roster_id)` as the join key is cleaner and follows the existing pattern where related data lives in separate tables (e.g., `manager_pitch_angles` is separate from `manager_profiles`).

**Confidence:** HIGH (design based on direct inspection of profiling_repo.py upsert pattern and STATE.md schema concern).

---

## Sleeper API Integration

### Endpoint to Add: `fetch_draft_picks(draft_id)`

The Sleeper API endpoint for draft picks is `GET /draft/{draft_id}/picks`. This returns an array of pick objects, each containing:
- `pick_no` — overall pick number
- `round` — round number
- `roster_id` — roster that made the pick
- `player_id` — player selected
- `picked_by` — user_id

The `fetch_drafts(league_id)` method already exists in `SleeperClient` (line 69). Phase 12 adds `fetch_draft_picks(draft_id)` as a new method following the same `_get()` retry pattern.

```python
# Add to SleeperClient
async def fetch_draft_picks(self, draft_id: str) -> list[dict[str, Any]]:
    try:
        result = await self._get(f"/draft/{draft_id}/picks")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return []
        raise
    return list(result or [])
```

**Confidence:** MEDIUM — Sleeper API docs are not in Context7; endpoint URL is from community knowledge. The existing `fetch_drafts()` pattern and the `fetch_transactions()` 404-guard pattern are HIGH confidence from direct code inspection. The specific `/draft/{draft_id}/picks` URL follows the documented Sleeper API convention visible in the codebase comments.

### Mapper: `map_draft_pick_selections()`

New static method on `SleeperMapper` following the `map_draft_slots()` pattern (lines 141–165 in `sleeper_mapper.py`). Accepts raw picks array, `league_id`, `draft_id`, `season`, and `draft_type` string. Returns a list of domain objects for insertion.

### On-Demand Step (D-11)

Draft pick ingestion is NOT wired into the standard `IngestService.run_full_ingest()` flow. It is invoked via a dedicated endpoint (e.g., `POST /league/{leagueId}/ingest/draft-picks`) that the user calls manually or via the UI. This prevents slow Sleeper fetches from blocking the main ingest run.

---

## Evidence Threshold Recommendation

**`MIN_ROOKIE_PICK_EVIDENCE` recommended value: 5**

Rationale:
- Phase 4 set `MIN_TRADE_EVIDENCE_THRESHOLD = 10` for trade-based profiling, where a trade involves multiple players and more complex behavioral signal
- Pick trades are a subset of all trades — a manager with 20 total trades may have only 3–5 where picks were involved
- Startup draft provides 12–16 selections per manager (roughly 4 rounds × 12 picks / 12 managers = 4 picks per manager per round, so ~16 total in a 4-round startup)
- A threshold of 5 means: 5 combined pick-trade transactions + draft selections before the "Draft & Picks" tab becomes visible
- This allows the tab to appear for managers with even modest pick-trade activity, while still requiring more than 1–2 data points
- Signal quality: 5 observations is sufficient for a directional read on positional tendency in a startup draft (12+ selections total often exist)

**PICK_PREMIUM_THRESHOLD for "picks buyer" badge/reroute: 0.10**

Rationale: This mirrors the `negatives = [delta for delta in position_deltas if delta < -0.10]` threshold already used in `_classify_exploitation()` (profiling_engine.py line 329). A consistent value-leak of 0.10+ normalized units when acquiring picks signals meaningful premium behavior.

**Minimum pick-trade evidence for premium scoring: 3**

Below 3 pick-trade transactions, `pick_premium_score` is `None` (not 0.0). A score of 0.0 means the manager is fair-value — `None` means no evidence to compute at all. This distinction flows into D-17 (silent omission when `None`).

**Confidence:** MEDIUM — threshold values are reasoned from codebase patterns; exact optimal values require real league validation.

---

## Frontend API Contract

Phase 12 requires the profiling API endpoint to return rookie/pick profile data alongside the existing `ManagerProfile`. Two options:

**Option A (recommended): Extend profiling endpoint response**
Add optional fields to `ManagerProfile` Pydantic model (or a companion field in the endpoint response):
```python
class ManagerProfile(BaseModel):
    # ... existing fields ...
    pick_premium_score: float | None = None
    pick_trade_evidence: int = 0
    positional_tendency: dict[str, float] = {}
    dominant_archetype: str | None = None
    archetype_pattern: dict[str, int] = {}
    show_draft_picks_tab: bool = False
    draft_selection_history: list[dict] = []
```

**Option B: Separate endpoint**
`GET /league/{leagueId}/managers/{rosterId}/rookie-pick-profile`

Option A is recommended because the frontend already fetches `ManagerProfile` for the dossier in a single `useQuery` call (`managerProfileOptions` in the dossier route). Adding the new fields to the same response avoids a second network roundtrip and keeps the dossier loading state unified.

The `show_draft_picks_tab` boolean flag is critical — it is the gate for D-02 (tab hidden below threshold). The frontend checks this flag before rendering the 4th tab button.

**Confidence:** HIGH — frontend query pattern verified by reading `managers.$managerId.tsx` lines 25–26.

---

## Component Contracts (from UI-SPEC)

The UI-SPEC is complete and approved. Key contracts:

| Component | File | Pattern to Follow |
|-----------|------|------------------|
| `DossierDraftPicksTab` | `components/DossierDraftPicksTab.tsx` | Match `DossierTradeHistoryTab` table structure; `overflow-x-auto rounded-xl border border-border/40 bg-card/45` |
| `RookiePickMarketCard` | `components/RookiePickMarketCard.tsx` | Match `<Card><CardContent>` pattern from `DossierOverviewTab.tsx` |
| Tab bar extension | `managers.$managerId.tsx` lines 102–116 | Add `{ key: "draft-picks", label: "Draft & Picks" }` conditionally; extend `useState` union type |
| "Picks Buyer" badge | `ManagerListRow.tsx` | `<Badge variant="default">Picks Buyer</Badge>` — absent when `pick_premium_score` is null or thin |
| Loading skeletons | Per UI-SPEC | `<Skeleton className="h-10 w-full" />` × 3 in `space-y-3` for tab; `<Skeleton className="h-24 w-full" />` for card |

Color discipline (from UI-SPEC):
- "Picks Buyer" badge: `variant="default"` (cyan `--primary`) — consistent with exploitability badge treatment
- Pick-premium indicator in Overview: `variant="secondary"` (mint `--accent`)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry logic for new Sleeper endpoint | Custom retry wrapper | `tenacity` already wired into `SleeperClient._get()` | Retry logic already handles 429/500/502/503/504 |
| Pick value normalization | Custom round→value table | `PICK_VALUE_NORMALIZED` from `profiling/constants.py` | Already calibrated; reuse prevents divergence |
| Archetype label assignment | New classification logic | `RookieEngine._assign_archetype()` from `rookie_engine.py` | Phase 7 labels already cover all positions; Phase 12 retroactively applies them |
| DuckDB upsert pattern | Custom INSERT logic | `profiling_repo.py` upsert pattern (lines 30–73) | Handles ID generation, ON CONFLICT, JSON serialization |
| Frontend data fetching | Custom fetch | `useQuery` with `managerProfileOptions` | TanStack Query is the project standard; already handling the dossier fetch |

---

## Common Pitfalls

### Pitfall 1: Schema Triple-Write Omission
**Risk:** Adding `draft_pick_selections` and `manager_rookie_pick_profiles` to the Alembic migration only. Tests that use `conftest.py` will fail to find the table. New user deployments will fail silently if `startup_tasks.py` is not updated.
**Prevention:** After writing migration 015, immediately add both tables to `_SCHEMA_COMPAT_TABLES` in `startup_tasks.py` AND to the test schema bootstrap in `conftest.py`.
**Source:** STATE.md "Schema: Dual schema management" concern; verified in `startup_tasks.py` lines 18–134.

### Pitfall 2: Startup Draft Slot Aggression (D-09 Violation)
**Risk:** Computing "how early did they pick relative to their slot" using startup draft slot numbers. This is explicitly invalid per D-09 — startup slots don't carry the same meaning as rookie-only draft slots.
**Prevention:** The engine computes positional share comparison only, not slot aggression. The UI-SPEC includes explicit copy: "Startup draft only — slot aggression analysis not applicable."

### Pitfall 3: `pick_premium_score = 0.0` vs. `None`
**Risk:** Treating a score of `0.0` (fair value) the same as no evidence computed. A manager with 10 pick trades and a 0.0 average delta is not the same as a manager with 0 pick trades.
**Prevention:** Use `float | None` for `pick_premium_score`. `None` = no evidence. `0.0` = evidence exists, no premium detected. Silent omission (D-17) applies to `None` only.

### Pitfall 4: Tab State Type Union Not Extended
**Risk:** Adding "Draft & Picks" tab button in the UI without extending the `useState` type union from `"overview" | "trade-history" | "pitch-angles"` to include `"draft-picks"`. TypeScript will not error on the button render but will fail on the conditional `tab === "draft-picks"` check.
**Prevention:** Update the `useState` generic type at line 22 of `managers.$managerId.tsx` in the same task as adding the tab.

### Pitfall 5: Draft Pick Fetch Blocks Ingest (D-11 Violation)
**Risk:** Wiring `fetch_draft_picks()` into `IngestService.run_full_ingest()`. Sleeper's draft endpoint can return large payloads and is not rate-limited the same way.
**Prevention:** Draft pick ingestion is always a standalone `POST /league/{leagueId}/ingest/draft-picks` endpoint, never called from the main ingest flow.

### Pitfall 6: `RerouteResult.reroute_type` Literal Not Extended
**Risk:** Adding "picks buyer" reroute logic in `reroute_engine.py` without extending the `Literal` in `trade/models.py`. Pydantic v2 will raise a `ValidationError` at runtime when the reroute object is constructed.
**Prevention:** Extend `reroute_type: Literal["better_target", "better_package", "picks_buyer"]` in `trade/models.py` before implementing the reroute logic.

### Pitfall 7: Manager Tendency Warning in Draft Room Requires League Context
**Risk:** Building manager tendency warnings that fire on every draft room request regardless of which managers are in the league. Warnings must be scoped to managers in the specific league being drafted in.
**Prevention:** `RookiePickProfileEngine.compute_tendency_warnings(league_id)` queries only managers in that league. The draft room endpoint passes `league_id` to this method.

---

## Code Examples

### Archetype Mapping from Existing Logic

From `backend/src/fantasy/rookie/rookie_engine.py` lines 230–273 (verified):

The archetype assignment checks metadata fields: `slot_rate`, `forty`, `weight`, `target_share`, `receiving_back`, `mobile`, `rush_yards`, etc. When retroactively mapping startup draft picks, these fields come from the `players` table's metadata blob. If metadata is sparse (startup-era picks for players no longer on roster), fall back to position-based dominant label.

```python
def _map_draft_selection_to_archetype(self, player_id: str) -> str | None:
    row = self._conn.execute(
        "SELECT position, metadata FROM players WHERE player_id = ?",
        [player_id]
    ).fetchone()
    if row is None:
        return None
    raw_player = {"position": row[0], "metadata": json.loads(row[1] or "{}"), "avg_fantasy_points": 0.0}
    # Delegate to existing RookieEngine logic
    return self._assign_archetype(raw_player)
```

### Evidence Count Convention

```python
# From profiling_engine.py line 719 (verified)
low_confidence = len(trades) < MIN_TRADE_EVIDENCE_THRESHOLD

# Phase 12 analog — in RookiePickProfileEngine:
evidence_count = len(pick_trades) + len(draft_selections)
show_draft_picks_tab = evidence_count >= MIN_ROOKIE_PICK_EVIDENCE
pick_premium_eligible = len(pick_trades) >= MIN_PICK_TRADE_FOR_PREMIUM  # = 3
```

### Frontend Tab Guard (from UI-SPEC + existing tab pattern)

```typescript
// Current state type in managers.$managerId.tsx line 22:
const [tab, setTab] = useState<"overview" | "trade-history" | "pitch-angles">("overview")

// Phase 12 extension:
const [tab, setTab] = useState<"overview" | "trade-history" | "pitch-angles" | "draft-picks">("overview")

// Tab array extension — conditionally include 4th tab:
const tabs = [
  { key: "overview", label: "Overview" },
  { key: "trade-history", label: "Trade History" },
  { key: "pitch-angles", label: "Pitch Angles" },
  ...(profile.show_draft_picks_tab ? [{ key: "draft-picks", label: "Draft & Picks" }] : []),
]
```

---

## Validation Architecture

Every major capability in Phase 12 requires acceptance tests. The following defines what each test must verify.

### V-01: RookiePickProfileEngine — pick-premium computation
- **Test:** Given a manager with 5 pick-trade transactions where they consistently overpaid (value delta -0.15 average), `pick_premium_score` should be approximately `+0.15` (positive = overpayer).
- **Test:** Given a manager with 0 pick-trade transactions, `pick_premium_score` should be `None`.
- **Test:** Given a manager with 2 pick-trade transactions (below `MIN_PICK_TRADE_FOR_PREMIUM`), `pick_premium_score` should be `None`.
- **File:** `backend/tests/rookie_pick/test_rookie_pick_engine.py`

### V-02: Positional tendency computation
- **Test:** Given a startup draft where manager A took WR in 6 of 12 picks (50% WR) and the league average WR rate was 30%, positional tendency for WR should be approximately `+0.20`.
- **Test:** Given a manager with no draft selections, `positional_tendency` returns empty dict.
- **File:** `backend/tests/rookie_pick/test_rookie_pick_engine.py`

### V-03: Evidence threshold and tab visibility
- **Test:** Manager with `evidence_count < MIN_ROOKIE_PICK_EVIDENCE` produces `show_draft_picks_tab = False`.
- **Test:** Manager with `evidence_count >= MIN_ROOKIE_PICK_EVIDENCE` produces `show_draft_picks_tab = True`.
- **Test:** Both cases: signals are still computed (not skipped) even when `show_draft_picks_tab = False`.
- **File:** `backend/tests/rookie_pick/test_rookie_pick_engine.py`

### V-04: Silent omission from integration surfaces (D-17)
- **Test:** Package builder with counterparty `pick_premium_score = None` — no structural change to offer, no mention of pick tendency in reasoning.
- **Test:** Package builder with counterparty `pick_premium_score = 0.20` and `pick_trade_evidence >= MIN_ROOKIE_PICK_EVIDENCE` — offer structure includes a pick.
- **Test:** Reroute engine with counterparty `pick_premium_score = None` — no "picks_buyer" reroute generated.
- **Test:** Reroute engine with counterparty `pick_premium_score = 0.20` and sufficient evidence — "picks_buyer" reroute appears.
- **File:** `backend/tests/picks/test_package_builder.py`, `backend/tests/picks/test_reroute_engine.py`

### V-05: Archetype mapping from Phase 7 vocabulary
- **Test:** Given a draft selection of a WR player with `slot_rate = 0.60` in their metadata, `archetype_label` should be `"Slot Receiver"`.
- **Test:** Given a draft selection where player metadata is absent, `archetype_label` falls back to `None` (not an empty string, not an error).
- **File:** `backend/tests/rookie_pick/test_rookie_pick_engine.py`

### V-06: Sleeper draft pick ingestion
- **Test:** `SleeperClient.fetch_draft_picks()` returns empty list on 404 (not an exception).
- **Test:** `SleeperMapper.map_draft_pick_selections()` correctly maps `pick_no`, `round`, `roster_id`, `player_id` from raw Sleeper picks array.
- **Test:** Draft pick ingestion does NOT appear in `IngestService.run_full_ingest()` call path (architectural check).
- **File:** `backend/tests/ingestion/test_sleeper_client.py`, `backend/tests/ingestion/test_sleeper_mapper.py`

### V-07: Schema triple-write
- **Test (startup_tasks):** Both `draft_pick_selections` and `manager_rookie_pick_profiles` appear in `_SCHEMA_COMPAT_TABLES`.
- **Test (conftest):** Test suite initializes both tables correctly; no `OperationalError: Table does not exist` in any Phase 12 integration test.
- **Test (migration):** `alembic upgrade head` from a fresh DB creates both tables with expected columns.
- **File:** `backend/tests/test_startup_tasks.py` (existing file — add new table assertions)

### V-08: API response shape
- **Test:** `GET /league/{leagueId}/managers/{rosterId}` returns response including `show_draft_picks_tab`, `pick_premium_score`, `positional_tendency`, `dominant_archetype`.
- **Test:** When `show_draft_picks_tab = False` in the response, `draft_selection_history` is empty (no data leak for hidden tab).
- **File:** `backend/tests/integration/test_profiling_router.py` (extend existing)

### V-09: Draft room manager tendency warnings
- **Test:** Manager with documented WR preference in startup draft produces `TendencyWarning` with `warning_type = "manager_tendency"` in draft room result.
- **Test:** Manager with `pick_premium_score = None` produces no manager tendency warning in draft room.
- **Test:** Warning title follows format `"[Manager Name] targets [Position] early"`.
- **File:** `backend/tests/picks/test_rookie_engine.py` (extend existing draft room tests)

---

## Confidence Summary

| Finding | Confidence | Source |
|---------|-----------|--------|
| Standalone engine pattern (not subclass) | HIGH | Direct code: `rookie_engine.py`, `profiling_engine.py` |
| PICK_VALUE_NORMALIZED values | HIGH | Direct code: `profiling/constants.py` |
| Schema triple-write requirement | HIGH | Direct code: `startup_tasks.py` + STATE.md |
| WarningType Literal extension | HIGH | Direct code: `rookie/models.py` |
| RerouteResult Literal extension | HIGH | Direct code: `trade/models.py` |
| Phase 7 archetype vocabulary | HIGH | Direct code: `rookie_engine.py` |
| Upsert pattern (DuckDB) | HIGH | Direct code: `profiling_repo.py` |
| Migration 015 is next | HIGH | Direct: alembic/versions/ directory listing |
| Package builder integration point | HIGH | Direct code: `package_builder.py` lines 26–50 |
| Sleeper `/draft/{id}/picks` endpoint | MEDIUM | Community knowledge; not in Context7 |
| MIN_ROOKIE_PICK_EVIDENCE = 5 | MEDIUM | Reasoned from Phase 4 pattern + data sparsity context |
| PICK_PREMIUM_THRESHOLD = 0.10 | MEDIUM | Reasoned from `profiling_engine.py` line 329 threshold |

---

*Phase: 12-manager-rookie-pick-profiles*
*Researched: 2026-03-25*
