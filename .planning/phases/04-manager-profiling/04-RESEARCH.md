# Phase 4: Manager Profiling — Research

**Researched:** 2026-03-21
**Domain:** Manager behavioral analysis engine; trade value delta computation; exploitation type classification; pitch angle generation; FastAPI profiling router; DuckDB output tables; React/TanStack tabbed dossier UI; shadcn tabs/table/alert components
**Confidence:** HIGH (architecture, stack, integration points, UI patterns); MEDIUM (KTC/ADP value delta computation approach — no single canonical source; reasoning below); LOW (secondary exploitation type threshold — empirically reasonable range documented but not from an authoritative source)

---

## User Constraints

_Copied verbatim from 04-CONTEXT.md._

### Locked Decisions

| ID | Decision |
|----|----------|
| D-01 | Dossiers accessible from two paths: (1) `/league/:leagueId/managers` route listing all managers, and (2) Phase 3 exploit window manager rows become clickable links to the dossier |
| D-02 | Managers list view shows: manager name + team direction label + exploitability score (with evidence count always co-located, e.g., "74 | 14 trades") — no exploitation type on the list |
| D-03 | Managers list also shows the top 1 pitch angle per manager as a preview row beneath the score |
| D-04 | Route is league-scoped: `/league/:leagueId/managers` and `/league/:leagueId/managers/:managerId` — a manager in multiple leagues has separate dossiers per league |
| D-05 | Tabbed layout inside each dossier: three tabs — Overview | Trade History | Pitch Angles |
| D-06 | Overview tab contains: roster summary, likely direction (from Phase 2 DirectionResult), positional needs, exploitability score with evidence count, exploitation type(s), and aggregate trade stats |
| D-07 | Trade History tab contains: all trades involving this manager, grouped by recency, with value delta per trade surfaced |
| D-08 | Pitch Angles tab contains: 2–3 pre-computed pitch angles, each showing deal archetype label + what to send + what to avoid + one-sentence reasoning |
| D-09 | Primary + secondary exploitation type assignment — secondary labeled if evidence score clears a minimum threshold; primary shown prominently, secondary as secondary badge |
| D-10 | Signal mapping per type: value-loss trader (measurable KTC/ADP delta), timing-error trader (sold at trough/bought at peak), directionally-incoherent trader (trades contradict direction label), archetype-specific overpayer (routinely overpays for one asset category) |
| D-11 | Evidence shown as aggregate stats (e.g., "Lost value on 7 of 10 trades"), not individual trade callouts |
| D-12 | Pitch angles are pre-computed per dossier at profile build time — not generated on-demand |
| D-13 | Each pitch angle includes: deal archetype label + what to send + what to avoid + one-sentence reasoning |
| D-14 | 2–3 pitch angles per dossier; top 1 shown as preview on managers list |
| D-15 | Constant name: `MIN_TRADE_EVIDENCE_THRESHOLD = 10` — lives in `backend/src/fantasy/profiling/constants.py` |
| D-16 | Below threshold: full dossier shown with prominent LOW CONFIDENCE amber banner at top of Overview tab; exploitability score visually dimmed |
| D-17 | Exploitability score always displayed with evidence count co-located wherever it appears — "Exploitability: 74 | 14 trades" |

### Claude's Discretion

- Exact KTC/ADP value delta computation approach (research should inform this)
- Secondary type minimum threshold value (the % of primary evidence that triggers secondary label)
- Whether directional incoherence is computed against the manager's own stored direction label or inferred from their roster
- Specific Alembic migration number for Phase 4 tables (005 or 006 depending on Phase 3's migration count)
- Tailwind styling choices for LOW CONFIDENCE banner (destructive variant vs. warning amber — resolved in UI-SPEC: amber)

### Deferred Ideas (Out of Scope for Phase 4)

- Manager-specific pitch notes tailored to a specific trade target (TRADE-V2-01) — Phase 5
- On-demand pitch angle generation for a specific trade scenario — Phase 5
- Historical manager behavior comparison (how has behavior changed over seasons) — not in Phase 4

---

## Summary

Phase 4 is a behavioral analysis phase: consume `transactions` (trade records) from Phase 1 and `team_directions` from Phase 2, run a profiling engine to classify each manager's exploitation type, compute an exploitability score, and generate pre-computed pitch angles. Output is stored in two new DuckDB tables and surfaced via a new `/profiling` FastAPI router. The frontend adds two new TanStack Router routes using the Phase 3/4 UI design contracts.

The architecture follows the same engine-class pattern established in Phase 2's `intelligence/` package. A new `profiling/` package lives alongside `intelligence/` — same layout: `__init__.py`, `constants.py`, `models.py`, `profiling_engine.py`, `profiling_repo.py`. The router wires in via `app.include_router()` in `main.py`.

The single biggest technical decision in Phase 4 is **how to compute trade value delta** without access to real-time KTC API data. The answer is to use the `player_adp_baseline` table (already ingested in Phase 1) as the value proxy. ADP rank is converted to a normalized value score, and delta = (value received) − (value sent) per trade side. This is directionally correct for identifying systematic losers even if the absolute delta numbers are imprecise.

**Alembic migration number:** Phase 3 uses migration 005 (`005_league_snapshots.py`). Phase 4 must use **006** (`006_phase4_profiling_tables.py`), with `down_revision = "005_league_snapshots"`.

---

## Standard Stack

### Core (inherited — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | Read Phase 1/2 tables; write Phase 4 output tables | Already locked; analytical SQL for all aggregate queries |
| pydantic | 2.x | Domain models: ManagerProfile, ExploitationType, PitchAngle | Established pattern from Phase 1/2 |
| fastapi | 0.115.x | New `/profiling` router: GET `/profiling/managers`, GET `/profiling/managers/:id` | Established pattern from Phase 1/2/3 |
| polars | 1.x | Trade record aggregation before scoring | Already in stack |

### Frontend (inherited — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.x | Component layer | Locked in Phase 3 |
| TanStack Router | 1.x | File-based routing for new `/league/$leagueId/managers` routes | Established in Phase 3 |
| TanStack Query | 5.x | Data fetching for managers list and dossier endpoints | Established in Phase 3 |
| shadcn/ui | latest | Component primitives | Established in Phase 3; new components: tabs, table, alert |

### New shadcn Components (Phase 4 additions)

```bash
npx shadcn@latest add tabs table alert
```

No additional npm packages needed. The Phase 3 `card`, `badge`, `button`, `separator`, `skeleton` components are reused throughout Phase 4.

### New Backend Packages

None required. Full computation stack is already present.

**Version verification (run before planning execution):**
```bash
npm view @tanstack/react-router version
npm view @tanstack/react-query version
```

---

## Architecture Patterns

### Recommended Project Structure Extension

```
backend/src/fantasy/
├── profiling/                        # NEW — Phase 4 engines
│   ├── __init__.py
│   ├── constants.py                  # MIN_TRADE_EVIDENCE_THRESHOLD, EXPLOITATION_TYPE_*, PITCH_ARCHETYPES
│   ├── models.py                     # Pydantic: ManagerProfile, ExploitationClassification, PitchAngle
│   ├── profiling_engine.py           # Core classification engine
│   └── profiling_repo.py             # DuckDB read/write for profiling tables
├── routers/
│   ├── profiling.py                  # NEW — GET /managers, GET /managers/:id
│   └── [existing routers...]
└── [existing packages...]

frontend/src/
├── routes/
│   ├── league.$leagueId.managers.tsx          # NEW — managers list
│   └── league.$leagueId.managers.$managerId.tsx  # NEW — dossier
├── components/
│   ├── ManagerListRow.tsx             # NEW
│   ├── DossierPage.tsx                # NEW — Tabs container
│   ├── DossierOverviewTab.tsx         # NEW
│   ├── DossierTradeHistoryTab.tsx     # NEW
│   └── DossierPitchAnglesTab.tsx      # NEW

backend/alembic/versions/
└── 006_phase4_profiling_tables.py    # NEW — manager_profiles, manager_pitch_angles
```

### Pattern 1: Profiling Engine Class

**What:** `ProfilingEngine` is a stateless class accepting a DuckDB connection. It reads the `transactions` table (filtering `type = 'trade'`), cross-references `player_adp_baseline` for value delta computation, and reads `team_directions` for directional incoherence detection. Outputs a `ManagerProfile` Pydantic model.

**When to use:** All manager profile computation. The router calls the engine; the engine does not know about HTTP.

```python
# backend/src/fantasy/profiling/profiling_engine.py
import duckdb
from fantasy.profiling.models import ManagerProfile
from fantasy.profiling.constants import MIN_TRADE_EVIDENCE_THRESHOLD

class ProfilingEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def compute_profile(self, league_id: str, roster_id: int) -> ManagerProfile:
        trades = self._load_trades(league_id, roster_id)
        direction = self._load_direction(league_id, roster_id)

        evidence_count = len(trades)
        low_confidence = evidence_count < MIN_TRADE_EVIDENCE_THRESHOLD

        exploitation = self._classify_exploitation(trades, direction)
        exploitability_score = self._compute_score(trades, exploitation)
        pitch_angles = self._compute_pitch_angles(trades, exploitation, direction)

        return ManagerProfile(
            league_id=league_id,
            roster_id=roster_id,
            evidence_count=evidence_count,
            low_confidence=low_confidence,
            exploitability_score=exploitability_score,
            exploitation_primary=exploitation.primary_type,
            exploitation_secondary=exploitation.secondary_type,
            exploitation_evidence=exploitation.evidence_strings,
            pitch_angles=pitch_angles,
            # ...roster summary, positional needs from team_directions...
        )
```

### Pattern 2: Trade Value Delta Computation (ADP Proxy)

**What:** Because real-time KTC API data is not ingested (out of Phase 1 scope), trade value delta is computed using `player_adp_baseline.adp` rank as a value proxy. Lower ADP rank = higher value. Delta = sum(value received) − sum(value sent).

**Confidence:** MEDIUM — ADP rank is a valid directional proxy but will not catch short-term market moves. It is sufficient to identify systematic value-loss patterns over multiple trades.

**Approach:**
1. For each trade in `transactions` where `type = 'trade'`, parse `adds` and `drops` JSON columns. The `adds` key maps roster_id → list of player_ids received. The `drops` key maps roster_id → list of player_ids sent.
2. Join player_ids against `player_adp_baseline` to get ADP value. Convert ADP rank to a normalized 0.0–1.0 score: `value = 1.0 - (adp_rank / max_adp_rank)`. Players not in the baseline (unranked prospects, picks) receive a position-based default value from the constants.
3. Draft picks in `draft_picks` JSON are valued using the `ROUND_WEIGHTS` from `intelligence/constants.py` (R1=3.0, R2=2.0, R3=1.0, R4=0.5), normalized to the same 0.0–1.0 scale.
4. Per-trade delta: `delta = sum(received_values) - sum(sent_values)` from the target manager's perspective.
5. Aggregate across all trades: win_rate = (trades where delta > 0) / total_trades; avg_delta = mean(all deltas).

**Key design consideration:** The directional incoherence classifier does NOT need to infer direction from the roster — it should read `team_directions.primary_label` (Phase 2 output) directly. This avoids redundant computation and ensures consistency with what the user already sees. If `team_directions` has no row for this manager (Phase 2 not yet run), incoherence classification is skipped and labeled as "insufficient data."

### Pattern 3: Exploitation Type Classification

**What:** Rule-based classification of four types. Each type has a measurable signal from the trade history. Classification returns a primary type and optionally a secondary type.

**Type signals:**

| Type | Signal | Computation |
|------|--------|-------------|
| value-loss trader | Negative avg_delta + win_rate < 0.40 | Compute from ADP delta per trade |
| timing-error trader | Trades during player value trough or peak | Compare trade timestamps to `player_stats_weekly` performance window — sold during low production stretch (last 3 weeks before trade), or bought during peak production stretch |
| directionally-incoherent trader | Trades contradict direction label | Rebuilder selling picks / buying aging vets; contender selling starters / hoarding youth — inferred from `team_directions.primary_label` + trade asset type |
| archetype-specific overpayer | Routinely overpays for specific position/archetype | Group trades by received player position — if one position category has avg_delta < -0.10 across 3+ trades, that's an overpay pattern |

**Secondary type threshold (Claude's Discretion):** Recommend 40% of primary evidence strength. If primary type shows up in 7 of 10 trades, secondary type threshold is 3+ trades (40% of 7, rounded up). This is a LOW confidence value — it is a reasonable threshold with no authoritative source. The constant is `SECONDARY_TYPE_THRESHOLD_RATIO = 0.40` in `constants.py`.

**Evidence aggregate strings (D-11):**
- value-loss trader: "Lost value on {n} of {total} trades"
- timing-error trader: "Sold during value trough on {n} of {total} trades"
- directionally-incoherent trader: "{n} trades contradict {direction_label} direction"
- archetype-specific overpayer: "Overpaid for {position} in {n} of {n_applicable} trades"

### Pattern 4: Pitch Angle Pre-Computation

**What:** 2–3 pitch angles generated at profile-build time from a rules matrix keyed on exploitation type and direction label. Not LLM-generated — deterministic from `PITCH_ARCHETYPES` constant table.

**Design:**

```python
# constants.py
PITCH_ARCHETYPES: dict[str, dict] = {
    "value_loss_win_now": {
        "deal_archetype": "Win-now swap",
        "send_template": "aging starter + future pick",
        "avoid_template": "prospect-heavy packages",
        "reasoning_template": "This manager consistently receives less value than sent. Package aging starters they value at peak + a pick. Avoid prospect-heavy offers — they trade young assets away quickly."
    },
    "value_loss_rebuild": {
        "deal_archetype": "Rebuild accelerator",
        "send_template": "mid-tier pick + bench depth",
        "avoid_template": "win-now veterans",
        "reasoning_template": "This manager loses value trading even in rebuild mode. Offer picks at face value + depth they undervalue. Avoid veteran packages — they overprice their young assets."
    },
    "incoherent_seller": {
        "deal_archetype": "Pick acquisition",
        "send_template": "veteran starter",
        "avoid_template": "competing picks in same round",
        "reasoning_template": "This manager sells draft capital inconsistently. Buy their picks cheap by trading veterans they need for roster depth."
    },
    "archetype_overpayer_qb": {
        "deal_archetype": "QB premium extraction",
        "send_template": "QB2 or fringe starter QB",
        "avoid_template": "non-QB packages",
        "reasoning_template": "This manager routinely overpays for QB talent. Lead with QB and attach at market rate — they will overpay to add quarterback depth."
    },
    # ... additional archetypes
}
```

Pitch angle selection: given a manager's exploitation primary type + direction label, look up 2–3 applicable archetypes from the matrix. Top 1 archetype is stored as the list preview.

### Pattern 5: DuckDB Output Tables

**What:** Two new tables in Alembic migration 006.

```sql
-- 006_phase4_profiling_tables.py: op.execute() DDL (DuckDB-compatible)

CREATE TABLE IF NOT EXISTS manager_profiles (
    id                       INTEGER PRIMARY KEY,
    league_id                VARCHAR NOT NULL,
    roster_id                INTEGER NOT NULL,
    computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evidence_count           INTEGER NOT NULL,
    low_confidence           BOOLEAN NOT NULL,
    exploitability_score     FLOAT NOT NULL,      -- 0–100 integer-range float
    exploitation_primary     VARCHAR,              -- one of 4 type strings or NULL
    exploitation_secondary   VARCHAR,              -- one of 4 type strings or NULL
    exploitation_evidence    VARCHAR NOT NULL,     -- JSON dict: type -> evidence string
    roster_summary           VARCHAR,              -- JSON: direction, positional_needs
    aggregate_trade_stats    VARCHAR NOT NULL,     -- JSON: total_trades, win_rate, avg_delta
    UNIQUE (league_id, roster_id)
);

CREATE TABLE IF NOT EXISTS manager_pitch_angles (
    id                       INTEGER PRIMARY KEY,
    league_id                VARCHAR NOT NULL,
    roster_id                INTEGER NOT NULL,
    rank                     INTEGER NOT NULL,     -- 1 = top angle shown in list preview
    deal_archetype           VARCHAR NOT NULL,
    send_description         VARCHAR NOT NULL,
    avoid_description        VARCHAR NOT NULL,
    reasoning                VARCHAR NOT NULL,
    computed_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (league_id, roster_id, rank)
);
```

**Migration chain:** `down_revision = "005_league_snapshots"` — must match the exact revision string used in migration 005. Verify with `ls backend/alembic/versions/` before writing migration 006.

### Pattern 6: FastAPI Profiling Router

**What:** New router at `/profiling/` following the established pattern from `routers/deps.py`.

```python
# backend/src/fantasy/routers/profiling.py
from fastapi import APIRouter, Depends
import duckdb
from fantasy.routers.deps import get_read_db_conn
from fantasy.profiling.profiling_engine import ProfilingEngine

router = APIRouter(prefix="/profiling", tags=["profiling"])

@router.get("/leagues/{league_id}/managers")
def list_managers(league_id: str, conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn)):
    # Returns list of ManagerSummary (score + evidence + top pitch angle)
    ...

@router.get("/leagues/{league_id}/managers/{roster_id}")
def get_manager_dossier(league_id: str, roster_id: int, conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn)):
    # Returns full ManagerProfile
    ...

@router.post("/leagues/{league_id}/managers/compute")
def compute_all_profiles(league_id: str, conn = Depends(get_write_db_conn)):
    # Runs ProfilingEngine for all rosters in the league; writes to manager_profiles + manager_pitch_angles
    ...
```

Registration in `main.py`:
```python
from fantasy.routers import profiling
app.include_router(profiling.router)
```

### Pattern 7: Frontend Route Files (TanStack Router file-based routing)

**What:** Two new route files following Phase 3 conventions.

```
frontend/src/routes/
├── league.$leagueId.managers.tsx          # /league/:leagueId/managers
└── league.$leagueId.managers.$managerId.tsx  # /league/:leagueId/managers/:managerId
```

Both files export a `Route` created with `createFileRoute`. The managers list uses `useQuery` to fetch `/profiling/leagues/$leagueId/managers`. The dossier uses `useQuery` to fetch `/profiling/leagues/$leagueId/managers/$managerId`.

### Pattern 8: ExploitWindowRow Link Update (Phase 3 Modification)

**What:** The Phase 3 `ExploitWindowPanel` `<details>/<summary>` rows need a `href` prop and a "View Dossier" link inside the expanded content. The expand/collapse interaction is preserved — the link navigates only when the "View Dossier" element is clicked, not on summary click.

**File to modify:** `frontend/src/routes/league.$leagueId.tsx` (Phase 3 route file)

Also: a "View all managers" link must appear at the bottom of the `ExploitWindowPanel` pointing to `/league/:leagueId/managers`.

### Anti-Patterns to Avoid

- **Do not parse trade value delta from KTC API in real time** — KTC has no public API; use `player_adp_baseline` ADP rank as the value proxy. Document the limitation in the constants file.
- **Do not hardcode `10` as the evidence threshold in JSX** — the frontend should read `low_confidence: bool` from the API response, which is computed server-side against `MIN_TRADE_EVIDENCE_THRESHOLD`. This avoids the threshold value living in two places.
- **Do not compute directional incoherence from roster composition** — read `team_directions.primary_label` directly. If Phase 2 hasn't run, skip incoherence classification (label as "Insufficient data").
- **Do not generate pitch angles on-demand per trade scenario** — that is Phase 5's job. Phase 4 pitch angles are pre-computed general archetypes from the `PITCH_ARCHETYPES` constant matrix.
- **Do not add scikit-learn or pandas** — the profiling engine is rule-based, same as Phase 2. DuckDB + Polars handles all aggregation.
- **Do not use Alembic `op.create_table()`** — use `op.execute()` with raw DuckDB DDL. The existing migration pattern (`001`–`005`) all use `op.execute()` for DuckDB compatibility.
- **Do not install shadcn `Alert` with `variant="destructive"`** for the LOW CONFIDENCE banner — use the default `Alert` variant with amber Tailwind utilities applied via `className` (see UI-SPEC §Color section). Red would signal a broken state; amber signals a trust calibration.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Trade value delta | Custom KTC scraper | `player_adp_baseline` ADP rank proxy | KTC has no public API; ADP rank is already ingested and sufficient for directional pattern detection |
| Pitch angle text generation | LLM call at request time | `PITCH_ARCHETYPES` constant lookup at build time | Deterministic, fast, testable; on-demand LLM generation is Phase 5+ scope |
| Tabbed dossier UI | Custom tab implementation | shadcn `tabs` (TabsList, TabsTrigger, TabsContent) | Already in design contract; Radix handles keyboard navigation, accessibility, active state |
| Trade history table | Raw `<table>` HTML | shadcn `Table` (TableHeader, TableBody, TableRow, TableCell) | Already in design contract; consistent with existing component inventory |
| LOW CONFIDENCE banner | Custom alert div | shadcn `Alert` with amber className overrides | Already in design contract; provides correct semantic structure |
| Direction label lookup | Re-deriving from roster | Read `team_directions.primary_label` from DuckDB | Phase 2 already computed this; re-deriving introduces divergence risk |

**Key insight:** Phase 4's value is in the behavioral classification logic and the pre-computed pitch archetypes — not in building infrastructure. Every infrastructure problem (routing, data fetching, DuckDB writes, UI components) is already solved by Phase 1–3 patterns. Reuse aggressively.

---

## Common Pitfalls

### 1. `transactions` table contains non-trade records
**Trap:** The `transactions` table stores adds, drops, waivers, and trades. The `type` column must be filtered to `type = 'trade'` before any profiling computation. Failing to filter will inflate evidence count and corrupt delta calculations.
**Prevention:** All profiling queries against `transactions` must include `WHERE type = 'trade'`.

### 2. ADP value proxy gaps (unranked players)
**Trap:** Some players in trade history will not have a row in `player_adp_baseline` (injured reserves, cut players, unranked prospects). Joining to `player_adp_baseline` without handling NULLs will drop those assets from the delta calculation silently.
**Prevention:** Define a per-position fallback ADP value in `constants.py` (e.g., `ADP_FALLBACK_BY_POSITION = {"QB": 0.05, "RB": 0.05, "WR": 0.05, "TE": 0.03, "PICK": 0.10}`). Use `COALESCE` in the DuckDB query or handle in the engine.

### 3. Draft pick value scaling
**Trap:** `ROUND_WEIGHTS` from Phase 2 (`R1=3.0, R2=2.0, R3=1.0, R4=0.5`) are on a different scale than the ADP-normalized 0.0–1.0 player values. Mixing them directly in delta calculation produces distorted results.
**Prevention:** Normalize pick values to the same 0.0–1.0 scale before summing. Define `PICK_VALUE_NORMALIZED = {1: 0.70, 2: 0.45, 3: 0.25, 4: 0.10}` in `profiling/constants.py` (derived from round weights, normalized to max of 0.70 to keep below top player values).

### 4. Alembic migration revision chain
**Trap:** Phase 3's migration 005 revision string must be used as `down_revision` in migration 006. Using the filename instead of the revision ID field will break `alembic upgrade head`.
**Prevention:** Before writing 006, run `grep "revision" backend/alembic/versions/005_league_snapshots.py` to get the exact revision string, then use it verbatim in `down_revision`.

### 5. Roster ID vs. Owner ID confusion
**Trap:** The `transactions.roster_ids` column is a JSON array of roster IDs (integers), not owner/user IDs. Manager identity in this system is by `roster_id` within a league. The `rosters.owner_id` column stores the Sleeper user ID string. Profiling is keyed on `(league_id, roster_id)` throughout.
**Prevention:** All profiling tables and engine methods use `roster_id` (integer) as the manager identifier, consistent with Phase 2's `team_directions` and `team_scorecards` tables.

### 6. Directional incoherence when Phase 2 has not run
**Trap:** If the user has not yet run Phase 2 engines, `team_directions` will have no rows for this league. The incoherence classifier will crash or return wrong results if it assumes a direction label exists.
**Prevention:** `ProfilingEngine._load_direction()` must handle NULL/missing gracefully — if no direction row exists, `directionally_incoherent` classification is skipped and returns `{"type": "directionally-incoherent trader", "status": "insufficient_data", "evidence": "Direction label not computed"}`.

### 7. Pitch angle preview on managers list with no angles
**Trap:** If a manager has fewer trades than needed to compute any pitch angle, the list row must show the empty-state copy rather than a blank or NULL.
**Prevention:** Per UI-SPEC copywriting contract, empty preview copy is: "Insufficient trade history for pitch angle." The backend API response for `pitch_angles` must be an empty list `[]`, not null. Frontend checks `pitch_angles.length === 0`.

### 8. `transactions.adds` / `transactions.drops` JSON parsing
**Trap:** The `adds` and `drops` columns store Sleeper's API response JSON directly, which maps `roster_id_string -> [player_id, ...]`. For a trade, both sides of the transaction are represented. The target manager's "received" players are in `adds[roster_id]` and "sent" players are in `drops[roster_id]`.
**Prevention:** Write a dedicated `_parse_trade_sides(transaction_row, roster_id)` helper that extracts `(received: list[str], sent: list[str])` and unit-test it with fixture data before wiring into the engine.

### 9. ExploitWindowRow modification breaks Phase 3 tests
**Trap:** Adding `href` to the Phase 3 `ExploitWindowPanel` may break existing Phase 3 component tests if they snapshot-test the rendered HTML.
**Prevention:** Update Phase 3 component tests when modifying `ExploitWindowRow`. The expand/collapse behavior (summary click toggles details) must be preserved — only the "View Dossier" inner link navigates.

### 10. `MIN_TRADE_EVIDENCE_THRESHOLD` in two places
**Trap:** If the frontend hardcodes `10` in the JSX condition instead of reading `low_confidence` from the API, the threshold will drift if the backend constant is ever changed.
**Prevention:** Backend API response includes `low_confidence: bool` field computed from `evidence_count < MIN_TRADE_EVIDENCE_THRESHOLD`. Frontend uses only this boolean for dimming/banner logic. The constant value 10 lives only in `backend/src/fantasy/profiling/constants.py`.

---

## Code Examples

### Example 1: Constants file structure

```python
# backend/src/fantasy/profiling/constants.py

# Evidence floor for reliable profiling (Source: CONTEXT.md D-15)
MIN_TRADE_EVIDENCE_THRESHOLD: int = 10

# Secondary type threshold: if secondary evidence >= this fraction of primary evidence count, label it
# LOW confidence value — 0.40 is domain-reasonable but not from an authoritative source
SECONDARY_TYPE_THRESHOLD_RATIO: float = 0.40

# ADP-based normalized player value fallback for players not in player_adp_baseline
# Used when a traded player has no ADP row (injury, cut, unranked prospect)
ADP_FALLBACK_BY_POSITION: dict[str, float] = {
    "QB": 0.05,
    "RB": 0.05,
    "WR": 0.05,
    "TE": 0.03,
    "K": 0.01,
    "DEF": 0.01,
    "UNKNOWN": 0.03,
}

# Draft pick normalized values (derived from Phase 2 ROUND_WEIGHTS, scaled to 0.0-1.0)
# Note: Phase 2 ROUND_WEIGHTS are {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}; max=3.0 → R1=1.0*0.70
PICK_VALUE_NORMALIZED: dict[int, float] = {
    1: 0.70,
    2: 0.45,
    3: 0.25,
    4: 0.10,
}

# Exploitability score computation weights per exploitation type signal
EXPLOITATION_TYPE_WEIGHTS: dict[str, float] = {
    "value_loss": 0.40,
    "timing_error": 0.25,
    "directional_incoherence": 0.20,
    "archetype_overpay": 0.15,
}
```

### Example 2: Pydantic domain models

```python
# backend/src/fantasy/profiling/models.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional

class PitchAngle(BaseModel):
    model_config = ConfigDict(frozen=False)
    rank: int
    deal_archetype: str
    send_description: str
    avoid_description: str
    reasoning: str

class ExploitationClassification(BaseModel):
    model_config = ConfigDict(frozen=False)
    primary_type: Optional[str]  # one of 4 strings or None
    secondary_type: Optional[str]
    evidence_strings: dict[str, str]  # type -> "Lost value on 7 of 10 trades"

class ManagerProfile(BaseModel):
    model_config = ConfigDict(frozen=False)
    league_id: str
    roster_id: int
    computed_at: str
    evidence_count: int
    low_confidence: bool
    exploitability_score: float  # 0–100
    exploitation_primary: Optional[str]
    exploitation_secondary: Optional[str]
    exploitation_evidence: dict[str, str]
    pitch_angles: list[PitchAngle]
    aggregate_trade_stats: dict  # total_trades, win_rate, avg_delta
    roster_summary: Optional[dict]  # direction_label, positional_needs
```

### Example 3: Frontend LOW CONFIDENCE amber banner (shadcn Alert, amber override)

```tsx
// DossierOverviewTab.tsx
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangle } from "lucide-react"

function LowConfidenceBanner({ evidenceCount }: { evidenceCount: number }) {
  return (
    <Alert
      className="bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800"
    >
      <AlertTriangle className="h-4 w-4 text-amber-600" />
      <AlertTitle className="text-amber-800 dark:text-amber-300 text-xs font-semibold">
        LOW CONFIDENCE
      </AlertTitle>
      <AlertDescription className="text-amber-700 dark:text-amber-400">
        Based on {evidenceCount} trades (minimum 10 for reliable profiling).
        Treat all conclusions with skepticism.
      </AlertDescription>
    </Alert>
  )
}
```

### Example 4: Exploitability score co-location (mandatory format)

```tsx
// ManagerListRow.tsx — score display (Body/Label hybrid as per UI-SPEC)
function ExploitabilityScore({
  score,
  evidenceCount,
  lowConfidence,
}: {
  score: number
  evidenceCount: number
  lowConfidence: boolean
}) {
  return (
    <span className="text-xs text-muted-foreground">
      Exploitability:{" "}
      <span
        className={
          lowConfidence
            ? "text-muted-foreground opacity-75 font-semibold"
            : "text-primary font-semibold"
        }
      >
        {score}
      </span>
      {" | "}
      <span>{evidenceCount} trades</span>
    </span>
  )
}
```

---

## Integration Points

### Data Sources Phase 4 Reads

| Table | Phase Origin | What Phase 4 Uses |
|-------|-------------|-------------------|
| `transactions` | Phase 1 | Trade history: `type='trade'`, `adds`, `drops`, `draft_picks`, `roster_ids`, `created_at` |
| `player_adp_baseline` | Phase 1 | ADP rank → normalized value score for delta computation |
| `players` | Phase 1 | Player position (for ADP fallback lookup and archetype-specific overpayer detection) |
| `team_directions` | Phase 2 | `primary_label`, `approved_moves`, `discouraged_moves` — for incoherence detection and pitch angle selection |
| `rosters` | Phase 1 | `starters`, `players` — for roster summary in dossier Overview tab |

### Phase 3 Components Modified by Phase 4

| File | Modification |
|------|-------------|
| `frontend/src/routes/league.$leagueId.tsx` | `ExploitWindowRow` gains `href` prop; "View all managers" link added at bottom of `ExploitWindowPanel` |

### Phase 5 Consumes Phase 4

Phase 5's trade package builder will read `manager_profiles` and `manager_pitch_angles` to personalize trade package recommendations. The `exploitation_primary`, `exploitation_evidence`, and `pitch_angles` fields in `manager_profiles` are the primary Phase 5 inputs.

---

## Alembic Migration

**Migration number:** 006
**Filename:** `backend/alembic/versions/006_phase4_profiling_tables.py`
**Revision ID:** `"006_phase4_profiling_tables"`
**Down revision:** `"005_league_snapshots"` (verify exact string from `005_*.py` before writing)
**Pattern:** `op.execute()` with raw DuckDB DDL — same as migrations 001–005
**Tables created:** `manager_profiles`, `manager_pitch_angles`
**Downgrade:** `DROP TABLE IF EXISTS manager_pitch_angles; DROP TABLE IF EXISTS manager_profiles;` (angles first, profiles second — avoids ordering issues)

---

## Validation Architecture

### Backend test stubs (follow Phase 2 pattern)

```
backend/tests/
├── test_profiling_engine.py    # Unit tests: test_trade_filtering, test_delta_computation,
│                               # test_exploitation_classification, test_pitch_angle_generation,
│                               # test_low_confidence_flag, test_missing_direction_graceful
├── test_profiling_repo.py      # Repo tests: test_upsert_profile, test_upsert_pitch_angles,
│                               # test_list_managers, test_get_profile
└── test_profiling_router.py    # Router tests: test_managers_list_endpoint,
                                # test_manager_dossier_endpoint, test_compute_endpoint
```

### Key verifications

```bash
# Migration applies cleanly
cd backend && python -m alembic upgrade head

# Package importable
python -c "from fantasy.profiling.constants import MIN_TRADE_EVIDENCE_THRESHOLD; assert MIN_TRADE_EVIDENCE_THRESHOLD == 10"
python -c "from fantasy.profiling.models import ManagerProfile, PitchAngle, ExploitationClassification"

# Router registered
python -c "from fantasy.routers.profiling import router; print(router.prefix)"
# Expect: /profiling
```

---

## Discretion Resolutions (Claude's Decisions)

| Discretion Area | Resolution | Confidence | Rationale |
|-----------------|-----------|-----------|-----------|
| Value delta computation | ADP rank proxy from `player_adp_baseline` | MEDIUM | Only player valuation data already in the system; directionally correct for systematic pattern detection |
| Secondary type threshold | `SECONDARY_TYPE_THRESHOLD_RATIO = 0.40` | LOW | 40% of primary evidence is a reasonable floor to distinguish "also shows this pattern" from noise; not from authoritative source |
| Directional incoherence source | Read `team_directions.primary_label` directly | HIGH | Avoids redundant computation; ensures consistency with Phase 2 output; handle NULL gracefully |
| Alembic migration number | 006 | HIGH | Phase 3 uses 005 (`005_league_snapshots.py`) — confirmed from Phase 3 RESEARCH.md and plans |
| LOW CONFIDENCE banner styling | Amber (not destructive red) | HIGH | Resolved in 04-UI-SPEC.md — amber signals trust calibration, red signals broken state |
