# Phase 15 Research: Waiver & Startup Workflows

**Phase:** 15 — Waiver & Startup Workflows
**Requirements:** FS-05, FS-09
**Research date:** 2026-03-26

---

## User Constraints

No CONTEXT.md exists for this phase. Constraints are derived from the locked project decisions in STATE.md and ROADMAP.md.

**Locked decisions:**
- Backend: Python 3.12 / FastAPI / DuckDB / Polars
- Frontend: React 19 / Vite / TanStack Query / shadcn-ui (custom primitives, no components.json)
- Adapter-first: all Sleeper JSON parsing isolated in SleeperMapper; engines consume Pydantic domain models
- Data source: Sleeper API only (read-only)
- DuckDB 1.5.0, not SQLite — all DDL must target DuckDB
- Triple-write schema pattern: new tables must appear in Alembic migration, `startup_tasks.py` `_SCHEMA_COMPAT_TABLES`, and `conftest.py` test schema bootstrap
- Next Alembic migration number: 015 (014 is `phase11_lineup_tables.py`)

**Claude's Discretion:**
- FAAB bid-range algorithm inputs and weighting
- Startup build template definitions (contender / rebuild / balanced)
- Orphan intake checklist dimensions and scoring formula
- 30-day action plan data model structure (structured task list chosen over freeform document — see Architecture Patterns)

**Deferred / Out of Scope:**
- Automated trade submission (Sleeper API is read-only)
- Multi-league FAAB budget tracking across leagues (Phase 16 portfolio scope)
- Historical FAAB transaction analytics over multiple seasons (Phase 9 retrospective scope)

---

## Sleeper API: What Is Actually Exposed

**Confidence: HIGH** (verified against official Sleeper API docs at docs.sleeper.com)

### FAAB / Waiver state from rosters endpoint

`GET /v1/league/<league_id>/rosters` returns a `settings` object per roster containing:

| Field | Type | Meaning |
|-------|------|---------|
| `waiver_position` | integer | Current waiver priority rank (1 = highest priority) |
| `waiver_budget_used` | integer | FAAB dollars spent by this roster so far this season |
| `total_moves` | integer | Total add/drop moves made by this roster |

**Critical gap:** The league's total FAAB budget (e.g., $100 default) is in the league `settings` object returned by `GET /v1/league/<league_id>`, not the roster object. The field name is `waiver_budget` in the league settings blob. Remaining FAAB = `league.settings.waiver_budget - roster.settings.waiver_budget_used`. The `settings_blob` column already stores the full league settings JSON, so this is derivable without a new Sleeper call.

### Waiver type encoding

Sleeper supports three waiver types (verified via Sleeper support docs):
- **Rolling waivers** (default): successful claimer drops to last position; others move up
- **Reverse standings**: order resets weekly based on current standings
- **FAAB bidding**: blind sealed bids; highest bidder wins

The `waiver_type` field in `league.settings` encodes these as integers. The official docs do not enumerate the integer mapping. Based on community tooling (ffscrapr R package source) the mapping is: `0` = no waivers / free agency, `1` = rolling waivers, `2` = FAAB. Treat this as MEDIUM confidence — the mapping should be logged and surfaced as a `waiver_type_label` derived field.

### Transaction records for FAAB bids

`GET /v1/league/<league_id>/transactions/<week>` — already ingested in Phase 1. Waiver-type transactions include a `settings` object with `waiver_bid` field (e.g., `{"waiver_bid": 44}`). This is already available in the `transactions` table via the `TransactionRecord.draft_picks` passthrough. **The actual bid amount is not stored in a dedicated column.** Phase 15 must extract bid amounts from the raw transaction `settings_blob`.

**Limitation:** The transactions table stores `adds`, `drops`, and `draft_picks` but not the raw `settings` blob containing `waiver_bid`. The SleeperMapper.map_transactions method must be extended to pass through the settings object for waiver-type transactions.

### Free agent / waiver availability inference

Sleeper does not expose a dedicated free-agent endpoint. Availability is derived:
1. Fetch all rosters — collect all `players` arrays across all rosters
2. Any NFL player ID (from `/v1/players/nfl`) not present in any roster's `players` list is a free agent
3. `waiver_clear_days` and `waiver_day_of_week` in `league.settings` determine when players clear waivers vs. are immediately available as free agents

**Staleness risk:** Roster data is stale from the last ingest. FAAB budgets and waiver wire availability can change multiple times per day during the waiver processing window. The phase must surface an explicit data freshness warning on all waiver recommendations citing the last ingest timestamp.

---

## Standard Stack

### Core (all already present in this project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | API layer | Project standard |
| DuckDB | 1.5.0 | Persistence and analytics | Project standard |
| Pydantic v2 | 2.x | Domain models and API contracts | Project standard |
| httpx + tenacity | current | Sleeper API calls | Project standard |

### Supporting (no new dependencies required)

No new Python packages are needed for Phase 15. All computation is in-process using existing engines and DuckDB queries.

| Capability | Uses |
|-----------|------|
| FAAB bid range | Pure Python arithmetic on existing `ScorecardInputs` and `PlayerValue` models |
| Waiver availability | DuckDB set-difference query across `rosters` and `players` tables |
| Startup pick valuation | Existing `PickEngine` + `RookieEngine` outputs, re-contextualized for startup mode |
| Orphan intake scoring | Pure Python, reads from existing `intelligence_service`, `lineup`, `picks` outputs |
| 30-day action plan | Structured Pydantic list, persisted as JSON in DuckDB |

### Frontend (all already present)

| Component | Source |
|-----------|--------|
| Card, Badge, Button, Separator | `src/components/ui/` |
| lucide-react icons | Already installed |
| TanStack Query | Already installed |
| shadcn tabs | Already installed (used in DossierPage) |

**Installation:** No new packages needed.

**Version verification:** Run `npm view` before adding any package. No new packages are anticipated for this phase.

---

## Architecture Patterns

### Recommended Package Structure

```
backend/src/fantasy/waiver/
├── __init__.py
├── constants.py          # FAAB thresholds, urgency tiers, orphan scoring weights
├── models.py             # WaiverRecommendation, StartupContext, OrphanIntake, ActionPlan
├── waiver_engine.py      # FAAB bid range, free agent availability, waiver scoring
├── startup_engine.py     # Startup pick valuation, trade-up/down heuristics, build templates
├── orphan_engine.py      # Orphan intake scoring, 30-day action plan generation
└── waiver_repo.py        # DuckDB reads/writes for waiver and startup state
```

### Pattern 1: FAAB Bid Range Algorithm

**What:** Compute a bid range `(low, high, maximum)` for a given player targeting a given roster.

**Inputs:**
- `player_value`: from existing `PlayerValue` model (direction-adjusted lens_direction score)
- `remaining_faab`: derived as `league.settings.waiver_budget - roster.settings.waiver_budget_used`
- `league_median_remaining`: median FAAB remaining across all rosters (competitive positioning)
- `direction_label`: from `DirectionResult` — urgency modifier
- `positional_scarcity`: from `PlayerValue.comp_positional_scarcity`
- `calendar_week`: if Phase 13 (Context Awareness) is available, use it; otherwise derive from NFL state endpoint

**Algorithm (percentage-of-remaining-budget approach):**

```python
# Source: 4for4 and Football Absurdity FAAB research; adapted for dynasty
def compute_bid_range(
    player_value_score: float,      # 0-100 from ValuationEngine
    remaining_faab: int,            # dollars remaining
    league_median_remaining: int,
    direction_urgency: float,       # 0.0-1.0; contenders = 1.0, rebuilds = 0.3
    positional_scarcity: float,     # 0-100
    is_immediate_start: bool,
) -> tuple[int, int, int]:          # low, mid, high
    base_pct = player_value_score / 100.0 * 0.25   # max 25% of remaining for elite
    scarcity_adj = positional_scarcity / 100.0 * 0.05
    urgency_adj = direction_urgency * 0.05
    start_adj = 0.0 if is_immediate_start else -0.03

    mid_pct = base_pct + scarcity_adj + urgency_adj + start_adj
    mid_pct = max(0.01, min(0.60, mid_pct))   # floor 1%, ceiling 60%

    mid = int(remaining_faab * mid_pct)
    low = max(1, int(mid * 0.60))
    high = min(remaining_faab, int(mid * 1.40))
    return low, mid, high
```

**Free-agent determination (waiver_bid=0 threshold):**
- If computed `high` is 0 or player value is below `FREE_AGENT_VALUE_FLOOR` constant, the recommendation label is `"free_agent_only"` — surface explicitly as "Only worth a free post-waiver claim."
- `FREE_AGENT_VALUE_FLOOR = 15.0` (0-100 scale) — named constant, not magic number.

**When to use:** Called by `WaiverEngine.compute_recommendations(league_id, roster_id)`.

### Pattern 2: Free Agent Availability Derivation

```python
# Source: Sleeper API docs — no dedicated free-agent endpoint exists
def get_available_players(
    conn: duckdb.DuckDBPyConnection, league_id: str
) -> list[str]:
    """Returns player IDs not on any roster in this league."""
    rostered = conn.execute(
        """
        SELECT DISTINCT unnest(string_split(players, ',')) AS player_id
        FROM rosters
        WHERE league_id = ?
        """,
        [league_id],
    ).fetchall()
    rostered_ids = {row[0] for row in rostered if row[0]}

    all_nfl = conn.execute(
        "SELECT player_id FROM players WHERE status = 'Active'"
    ).fetchall()

    return [row[0] for row in all_nfl if row[0] not in rostered_ids]
```

Note: The `players` table is populated by the existing `SleeperClient.fetch_players()` call. The `status` field on the player record reflects NFL roster status (Active, Inactive, etc.), not fantasy availability.

### Pattern 3: Startup Draft Context

**What:** When `startup_mode = True` is detected (Sleeper draft status = `pre_draft` or `drafting`), the system enters startup draft mode.

**Startup pick valuation differs from dynasty trade values in two key ways:**
1. Startup picks map to actual player slots on the current draft board (slot 1.01, 1.02 etc.) — value is a function of who is available at that slot, not an abstract future pick
2. Trade-up/trade-down decisions are tier-break decisions: if 3+ players remain in the current tier, trade down; if you are 1 slot outside an elite tier break, trade up

**Build templates (direction-aware):**

| Template | Direction Alignment | Pick Priority | Player Age Priority |
|----------|--------------------|--------------|--------------------|
| `win_now` | true_contender, fragile_contender | Trade away for veterans | 27-30 yr peak |
| `balanced` | fringe_playoff, productive_struggle | Hold 1sts, trade 2nds for veterans | 24-27 yr ascending |
| `rebuild` | one_year_punt, elite_value_accumulation, hard_rebuild | Accumulate all picks | 21-24 yr upside |

**Trade-up/trade-down heuristics:**
- Trade **up**: current pick is 1-3 slots below the next tier break AND the target player has `lens_direction` score 20+ points above the next available player
- Trade **down**: 3+ equivalent players remain in current tier; accept any offer that yields a pick 2+ rounds later plus a future 1st-round pick

### Pattern 4: Orphan Intake Scoring

**Five evaluation dimensions (from dynasty community frameworks):**

| Dimension | Data Source | Weight | Scoring |
|-----------|-------------|--------|---------|
| Age curve health | roster player ages + `comp_age_curve` per player | 0.25 | % of starting value players aged 25 or younger |
| Pick capital | existing `PickEngine` output — pick values summed | 0.25 | Sum of `demand_adjusted_value` across all held picks |
| Dead roster spots | `HygieneEngine` cut suggestions | 0.20 | Count of players in `cut` bucket as % of roster size |
| Lineup viability | existing `LineupEngine` output | 0.20 | `total_lineup_score` normalized against league median |
| Liquidation options | `HygieneEngine` consolidate + `lens_market` score | 0.10 | Count of players with `lens_market` > 60 and positive trade evidence |

**Composite orphan score:** weighted sum → 0-100 scale. Score interpretation:
- 0-30: Distressed — major capital infusion or liquidation required
- 31-55: Rebuilder — clear direction but meaningful work needed
- 56-75: Balanced — capable of direction pivot with targeted moves
- 76-100: Ready to compete — may need 1-2 positional fills

### Pattern 5: 30-Day Action Plan

**Data model (Pydantic):**

```python
class ActionPlanItem(BaseModel):
    priority_rank: int
    category: Literal["add", "drop", "trade", "hold", "evaluate"]
    headline: str
    rationale: str
    urgency: Literal["this_week", "30_days", "offseason"]
    target_entity_type: Literal["player", "pick", "position", "manager"]
    target_entity_ids: list[str]
    confidence_label: Literal["HIGH", "MEDIUM", "LOW"]

class ActionPlan(BaseModel):
    league_id: str
    roster_id: str
    generated_at: str
    plan_type: Literal["orphan_intake", "startup", "new_connection"]
    items: list[ActionPlanItem]
    summary: str
```

This is a ranked task list, not a freeform document. It is generated once on demand and persisted to DuckDB. The user can regenerate it after re-ingest.

**Generation logic for orphan intake:**
1. Run `OrphanIntakeScorer.compute()` — get 5 dimension scores
2. For each dimension below threshold, emit 1-2 `ActionPlanItem` entries
3. Run `WaiverEngine.compute_recommendations()` — top 3 adds become `"add"` items
4. Run `HygieneEngine` consolidate/cut outputs — top cuts become `"drop"` items
5. Run `DirectionEngine` — approved moves become `"trade"` items
6. Sort all items by urgency then priority

### Anti-Patterns to Avoid

- **Polling Sleeper for FAAB budget mid-waiver window:** Sleeper processes waivers in batch. Do not attempt to infer mid-process state. Always show freshness timestamp and require user re-ingest.
- **Hard-coding the total FAAB budget:** Read from `settings_blob` on the `leagues` table. Default to 100 only when the field is absent.
- **Treating waiver_type=0 as FAAB:** Leagues with no waivers (`waiver_type=0`) should show waiver recommendations as "free agent pickup" with no bid logic.
- **Building startup mode as a separate app flow:** Startup detection is a flag on the existing league view (`draft_status` in the Sleeper draft response). Wire into the existing league team screen as conditional panels.
- **Storing action plan as unstructured text:** The Pydantic list model is required for downstream REC-01 compatibility in Phase 17.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Player value scoring | Custom player evaluator | Existing `ValuationEngine` + `PlayerValue.lens_direction` | Already direction-adjusted, format-adjusted |
| Pick value | Custom pick calculator | Existing `PickEngine.compute_pick_value()` | Already standings-aware, demand-adjusted |
| Roster hygiene | Custom cut/stash logic | Existing `HygieneEngine` | Already produces consolidate/cut/stash/taxi buckets |
| Startup player tier breaks | Custom ranking | Existing `RookieEngine` / `ValuationEngine` scores as tier input | Avoids duplicating scoring logic |
| Direction label | Custom team assessment | Existing `DirectionEngine` | Orphan and startup templates map directly to existing 8 direction labels |
| Team scorecard | Custom roster assessment | Existing `ScorecardEngine` | Orphan intake uses scorecard sub-scores directly |

---

## Common Pitfalls

### Pitfall 1: Stale FAAB Budget Inference
**Problem:** `waiver_budget_used` on the roster object reflects the last ingest. If waivers processed since then, the remaining budget calculation is wrong.
**Mitigation:** Surface a `data_freshness_warning` on every FAAB recommendation. Compute `hours_since_ingest` from `ingested_at` column on the `rosters` table. If > 12 hours, show a prominent stale-data badge. Never suppress this warning.

### Pitfall 2: Missing waiver_bid in stored transactions
**Problem:** The existing `SleeperMapper.map_transactions()` does not extract the `settings.waiver_bid` field — it is dropped during mapping. Historical FAAB bids are not available in the DB without a mapper extension.
**Mitigation:** Extend `TransactionRecord` to add `waiver_bid: int | None = None` and `SleeperMapper.map_transactions()` to extract `item.get("settings", {}).get("waiver_bid")`. Add a new column `waiver_bid` to the `transactions` table in migration 015. This enables bid history analysis (who bids aggressively, budget depletion patterns).

### Pitfall 3: waiver_type integer mapping is undocumented
**Problem:** Sleeper docs do not formally enumerate `waiver_type` integer values. The mapping (0=free, 1=rolling, 2=FAAB) is inferred from community wrappers.
**Mitigation:** Store the raw integer in DB. Derive a `waiver_type_label: str` at read time using a named mapping dict `WAIVER_TYPE_LABELS = {0: "free_agent", 1: "rolling", 2: "faab"}` with a fallback `"unknown"`. Surface the label on the UI — never silently assume FAAB.

### Pitfall 4: Startup mode detection from wrong source
**Problem:** A league might have `status=drafting` at the league level even after the draft completes if Sleeper hasn't updated.
**Mitigation:** Check `draft.status` from `GET /v1/league/<league_id>/drafts` (already in `SleeperClient.fetch_drafts()`). Only enter startup mode when `draft.status in ("pre_draft", "drafting")`.

### Pitfall 5: Orphan intake applied to healthy teams
**Problem:** Orphan intake is a specific workflow for newly acquired or abandoned teams. Applying it to active healthy teams produces confusing output.
**Mitigation:** Gate on a user-set `is_orphan` flag stored per roster. Do not auto-detect. Expose a UI toggle in the team settings panel.

### Pitfall 6: Free agent pool includes NFL-inactive players
**Problem:** The `/v1/players/nfl` endpoint includes injured reserve, practice squad, and retired players. Surfacing them as "available" is noise.
**Mitigation:** Filter the free agent pool to `status = "Active"` OR `status = "Injured Reserve"` (IR players are sometimes dynasty-relevant). Exclude `status in ("Inactive", "Suspended", "Retired")`.

### Pitfall 7: Bid range high end exceeds remaining budget
**Problem:** The `high` bid ceiling must never exceed `remaining_faab`. This can happen if the algorithm computes a high multiplier.
**Mitigation:** Enforce `high = min(remaining_faab, high)` as a hard clamp before returning bid range. Assert this in unit tests.

---

## Code Examples

### Extracting FAAB state from existing stored data

```python
# Source: Sleeper API docs + existing codebase patterns
def get_faab_state(conn, league_id: str, roster_id: int) -> dict:
    league_row = conn.execute(
        "SELECT settings_blob FROM leagues WHERE league_id = ?", [league_id]
    ).fetchone()
    settings_blob = json.loads(league_row[0] or "{}")
    total_budget = int(settings_blob.get("waiver_budget", 100))
    waiver_type_raw = int(settings_blob.get("waiver_type", 1))

    roster_row = conn.execute(
        """
        SELECT settings_blob FROM rosters
        WHERE league_id = ? AND roster_id = ?
        """,
        [league_id, roster_id],
    ).fetchone()
    # NOTE: roster settings_blob not currently stored — see Pitfall 2 note below
    # waiver_budget_used is in roster.settings, not currently persisted
    # Phase 15 P01 must extend the rosters table or re-derive from transactions
    ...
```

**Important:** The existing `rosters` table does NOT currently store `waiver_position` or `waiver_budget_used`. These fields are parsed by `SleeperMapper.map_roster()` but are not included in `RosterSnapshot` or the DB insert. **Phase 15 Plan 01 must add these two columns to the `rosters` table** (migration 015, startup_tasks, conftest).

### Detecting waiver type

```python
WAIVER_TYPE_LABELS: dict[int, str] = {
    0: "free_agent",   # no waivers — all adds are immediate free agents
    1: "rolling",      # priority-based rolling waivers
    2: "faab",         # blind FAAB bidding
}

def get_waiver_type_label(settings_blob: dict) -> str:
    raw = settings_blob.get("waiver_type", 1)
    try:
        return WAIVER_TYPE_LABELS.get(int(raw), "unknown")
    except (ValueError, TypeError):
        return "unknown"
```

### Extending SleeperMapper for waiver_bid

```python
# In SleeperMapper.map_transactions — extend to capture waiver_bid
payload = {
    ...
    "waiver_bid": item.get("settings", {}).get("waiver_bid") if item.get("type") == "waiver" else None,
}
```

---

## Schema Changes Required

Phase 15 introduces one new migration (015) with the following changes.

### Rosters table extension (ALTER)

```sql
-- Add to existing rosters table
ALTER TABLE rosters ADD COLUMN waiver_position INTEGER;
ALTER TABLE rosters ADD COLUMN waiver_budget_used INTEGER;
```

Must be added to `_SCHEMA_COMPAT_COLUMNS` in `startup_tasks.py` alongside the Alembic migration.

### New tables (CREATE)

```sql
-- Waiver recommendations cache
CREATE TABLE IF NOT EXISTS waiver_recommendations (
    id                  INTEGER PRIMARY KEY,
    league_id           VARCHAR NOT NULL,
    roster_id           INTEGER NOT NULL,
    computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recommendations_json VARCHAR NOT NULL,
    UNIQUE (league_id, roster_id)
);

-- Startup draft context
CREATE TABLE IF NOT EXISTS startup_contexts (
    id                  INTEGER PRIMARY KEY,
    league_id           VARCHAR NOT NULL UNIQUE,
    computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    draft_status        VARCHAR NOT NULL,
    build_template      VARCHAR NOT NULL,
    context_json        VARCHAR NOT NULL
);

-- Orphan intake assessments
CREATE TABLE IF NOT EXISTS orphan_intakes (
    id                  INTEGER PRIMARY KEY,
    league_id           VARCHAR NOT NULL,
    roster_id           INTEGER NOT NULL,
    computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    age_curve_score     FLOAT NOT NULL,
    pick_capital_score  FLOAT NOT NULL,
    dead_spots_score    FLOAT NOT NULL,
    lineup_viability_score FLOAT NOT NULL,
    liquidation_score   FLOAT NOT NULL,
    composite_score     FLOAT NOT NULL,
    intake_json         VARCHAR NOT NULL,
    UNIQUE (league_id, roster_id)
);

-- 30-day action plans
CREATE TABLE IF NOT EXISTS action_plans (
    id                  INTEGER PRIMARY KEY,
    league_id           VARCHAR NOT NULL,
    roster_id           INTEGER NOT NULL,
    computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    plan_type           VARCHAR NOT NULL,
    items_json          VARCHAR NOT NULL,
    summary             VARCHAR NOT NULL,
    UNIQUE (league_id, roster_id)
);
```

### Transactions table extension (ALTER)

```sql
ALTER TABLE transactions ADD COLUMN waiver_bid INTEGER;
```

---

## Validation Architecture

Each capability in this phase requires explicit acceptance tests. Tests live in `backend/tests/`.

### 1. FAAB Bid Range — `test_waiver_engine.py`

| Test | Input | Expected |
|------|-------|----------|
| Contender high urgency bid | player_value=85, remaining=80, direction=contender | high bid > 30% of remaining |
| Rebuild low urgency bid | player_value=85, remaining=80, direction=rebuild | high bid < 20% of remaining |
| Free agent only threshold | player_value=12, remaining=80 | label="free_agent_only", bid=(0,0,0) |
| Bid ceiling enforcement | player_value=90, remaining=15 | high <= 15 (remaining FAAB) |
| Zero budget | remaining=0 | returns free_agent_only regardless of player value |
| waiver_type != faab | waiver_type=1 (rolling) | returns waiver_priority recommendation, no dollar amounts |

### 2. Free Agent Availability — `test_waiver_engine.py`

| Test | Setup | Expected |
|------|-------|----------|
| Player on no roster | player_id="X" absent from all roster.players lists | "X" in available list |
| Player on any roster | player_id="Y" in one roster | "Y" not in available list |
| NFL-inactive player excluded | player status="Inactive" | not in available list |
| IR player included | player status="Injured Reserve" | in available list |

### 3. FAAB State Derivation — `test_waiver_engine.py`

| Test | Setup | Expected |
|------|-------|----------|
| Remaining budget calc | total_budget=100, waiver_budget_used=44 | remaining=56 |
| Missing waiver_budget defaults to 100 | settings_blob has no waiver_budget key | total_budget=100 |
| Stale data warning | ingested_at > 12 hours ago | response includes data_freshness_warning=True |

### 4. Orphan Intake Scoring — `test_orphan_engine.py`

| Test | Setup | Expected |
|------|-------|----------|
| All young roster | all players aged 22-24 | age_curve_score > 70 |
| No picks, old roster | zero held picks, avg age 30+ | composite_score < 35 |
| Dead spots count | 3 of 12 players in cut bucket | dead_spots penalizes composite |
| Score range | any valid roster | 0 <= composite_score <= 100 |

### 5. Startup Draft Mode Detection — `test_startup_engine.py`

| Test | Setup | Expected |
|------|-------|----------|
| Pre-draft detection | draft.status="pre_draft" | startup_mode=True |
| Drafting detection | draft.status="drafting" | startup_mode=True |
| Complete detection | draft.status="complete" | startup_mode=False |
| Build template assignment | direction="true_contender" | template="win_now" |
| Trade-up trigger | pick 1 slot below tier break, score gap >= 20 | trade_up=True |
| Trade-down trigger | 3+ equivalent players in tier | trade_down=True |

### 6. 30-Day Action Plan — `test_orphan_engine.py`

| Test | Setup | Expected |
|------|-------|----------|
| Items are sorted | mixed urgency items | sorted by urgency then priority |
| Non-empty for distressed team | composite_score < 30 | len(items) >= 5 |
| Category distribution | any orphan team | at least one "add" and one "drop" item present |
| Confidence enforcement | LOW confidence items | confidence_label="LOW" set correctly |

### 7. API Integration — `test_integration.py`

| Endpoint | Test | Expected |
|----------|------|----------|
| `GET /waiver/{league_id}/{roster_id}/recommendations` | valid league+roster | 200 with recommendations list |
| `GET /waiver/{league_id}/{roster_id}/recommendations` | waiver_type=free_agent | recommendations have no bid amounts |
| `POST /waiver/{league_id}/{roster_id}/orphan-intake` | valid orphan setup | 200 with composite_score and 5 dimension scores |
| `GET /waiver/{league_id}/{roster_id}/action-plan` | new orphan team | 200 with non-empty items list |
| `GET /startup/{league_id}/context` | drafting league | 200 with build_template and pick_valuations |

### 8. Frontend Verification (Human-Verify Checkpoint)

At the end of Phase 15's final plan:
1. Waiver wire panel shows top 3 add recommendations with bid ranges or "free agent only" label
2. Stale data badge appears when `hours_since_ingest > 12`
3. Startup mode panels appear only when `draft.status in ("pre_draft", "drafting")`
4. Orphan intake panel is gated behind the `is_orphan` toggle — hidden for non-orphan teams
5. 30-day action plan renders all items sorted by urgency, with confidence badges on LOW items
6. Bid range displays low/mid/high as three distinct values in monospace font

---

## Open Questions / LOW Confidence Items

| Question | Confidence | Recommended Approach |
|----------|------------|----------------------|
| `waiver_type` integer → string mapping | LOW | Log unknown values; expose raw integer in API response alongside derived label; validate against a real league |
| Whether `settings_blob` on the `leagues` table reliably contains `waiver_budget` | MEDIUM | Verified from Sleeper docs that it is in league settings; verify against actual league JSON in test fixtures |
| Sleeper `waiver_clear_days` / `waiver_day_of_week` field names in settings_blob | LOW | Parse from `settings_blob` during implementation; add to `conftest.py` fixtures |
| Whether `draft.status` is reliably updated by Sleeper in real-time | MEDIUM | Treat as best-available signal; surface freshness warning on startup mode detection |
