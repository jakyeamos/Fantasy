# Phase 10 Research: Pick Accuracy & Draft Order

**Researched:** 2026-03-23
**Phase:** 10-pick-accuracy-draft-order
**Requirement addressed:** FS-01

---

## User Constraints

> Copied verbatim from 10-CONTEXT.md. Planner MUST honor all locked decisions below.

### Locked Decisions

- **D-01:** Pick projections are **blocked** until the draft order rule is fully configured — no silent inverse-standings default for new leagues.
- **D-02:** Blocked pick surfaces show a **"Rule not configured" placeholder** (not a banner); the placeholder is clickable and navigates to the league settings rule editor.
- **D-03:** **All fields must be complete** before projections unblock — a partially configured rule keeps projections blocked.
- **D-04:** Each league is configured **independently** — no copy-from-league feature.
- **D-05:** **Lottery descoped entirely** — `LeagueDraftOrderRule` model excludes lottery fields; rule editor excludes lottery UI.
- **D-06:** **Consolation exceptions descoped** — `LeagueDraftOrderRule` model excludes consolation fields; rule editor excludes consolation UI.
- **D-07:** `LeagueDraftOrderRule` captures three fields: (1) non-playoff order basis (`inverse_standings` or `max_points_for`), (2) playoff-team ordering, (3) tiebreaker.
- **D-08:** Both `inverse_standings` and `max_points_for` are supported non-playoff order bases.
- **D-09:** Editor lives in **league settings** (`league.$leagueId.tsx`), not a separate tab.
- **D-10:** **Single-page form** — all three fields visible at once; no wizard/stepper.
- **D-11:** Citation uses the **same format everywhere** — consistent small inline text on all pick value surfaces.
- **D-12:** Citation is **clickable** — navigates to league settings rule editor.
- **D-13:** Citation text includes **both** order basis and playoff-team ordering rule (e.g., `"Using: Max PF order · Playoff teams by finish"`).
- **D-14:** "Rule not configured" placeholder is **also clickable** (same navigation target as the configured-state citation).

### Claude's Discretion

- Exact field names and enum values for `LeagueDraftOrderRule`.
- Whether `LeagueDraftOrderRule` is its own DB table or a JSONB column on `leagues`.
- Exact slot-projection algorithm for max-PF ordering vs. inverse-standings.
- How the pick engine receives the rule — injected into `PickValuationContext` or loaded by `PickRepo`.
- Alembic migration numbering (must not conflict with 009–011 already in use; next available is 012).

### Deferred Ideas

- Lottery configuration — excluded from Phase 10 scope.
- Consolation/toilet-bowl exceptions — excluded from Phase 10 scope.
- Copy draft order rule across leagues — excluded.

---

## Standard Stack

### Core (existing — do not change versions)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| DuckDB | 1.5.0 | All relational storage and query | Project-wide decision; all DDL targets DuckDB |
| FastAPI | current | API endpoints | Project-wide backend framework |
| Pydantic v2 | current | Domain models, request/response validation | Used in all existing models (`BaseModel`, `ConfigDict`) |
| Alembic | current | Schema migrations | Existing migration chain 001–011 |
| TanStack Query | current | Frontend data fetching, caching, mutations | All existing pick/league queries use it |
| shadcn/ui | initialized | UI component library | Project standard since Phase 3 |

### New shadcn Components to Install
```bash
npx shadcn@latest add radio-group label
```
- `radio-group` — non-playoff order basis field (2 options; RadioGroup preferred over Select per UI-SPEC D-10/implementation note 9)
- `label` — form field labels in DraftOrderRuleForm

### Supporting (already present)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| shadcn Select | Dropdown selects | Playoff ordering (3 options) and tiebreaker (3 options) fields |
| TanStack Router `<Link>` | Client-side navigation with hash | RuleCitation clickable link with `hash="draft-order-rule"` |
| `useMutation` (TanStack Query) | Save rule mutation | DraftOrderRuleForm save action |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate `league_draft_order_rules` table | JSONB column on `leagues` | Separate table is cleaner for CRUD and migration rollback; also matches the repo pattern in `LeagueRepo` |
| React Hook Form | Plain controlled form | 3-field form is simple enough for plain controlled state; no schema validation library needed |

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
backend/
├── alembic/versions/012_draft_order_rules.py   # new table: league_draft_order_rules
├── src/fantasy/
│   ├── picks/
│   │   ├── constants.py         # add NonPlayoffOrderBasis enum values
│   │   ├── models.py            # add LeagueDraftOrderRule, extend PickValuationContext + PickValue
│   │   ├── pick_engine.py       # replace expected_draft_slot() with rule-dispatching version
│   │   └── pick_repo.py         # add get_draft_order_rule(), save_draft_order_rule()
│   └── routers/
│       ├── picks.py             # unchanged (rule is loaded internally by engine)
│       └── leagues.py           # new: PUT /leagues/{league_id}/draft-order-rule
                                 # new: GET /leagues/{league_id}/draft-order-rule

frontend/
└── src/
    ├── api/
    │   ├── types.ts             # add LeagueDraftOrderRule, extend PickValue with rule_citation
    │   └── queries.ts           # add draftOrderRuleOptions, saveDraftOrderRuleMutation
    └── components/
        └── picks/
            └── RuleCitation.tsx # new shared component — citation string or unconfigured link
```

### Pattern 1: LeagueDraftOrderRule — Separate Table (RECOMMENDED)

**What:** Store the draft order rule as a separate `league_draft_order_rules` table keyed by `league_id`. One row per league, upserted on save.

**Why separate table over JSONB column on leagues:**
- Leagues table already has `settings_blob VARCHAR` for Sleeper-sourced settings; Phase 10 rule is user-authored, not Sleeper-sourced — keeping them separate avoids conflation.
- Separate table enables clean Alembic rollback.
- Follows the pattern already used for `manager_profiles`, `team_directions`, etc.
- `PickRepo.get_draft_order_rule(league_id) -> LeagueDraftOrderRule | None` matches existing repo patterns exactly.

**Table DDL (migration 012):**
```sql
CREATE TABLE IF NOT EXISTS league_draft_order_rules (
    id                   INTEGER PRIMARY KEY,
    league_id            VARCHAR NOT NULL UNIQUE,
    non_playoff_basis    VARCHAR NOT NULL,   -- 'inverse_standings' | 'max_points_for'
    playoff_ordering     VARCHAR NOT NULL,   -- 'by_finish' | 'by_record' | 'by_points_for'
    tiebreaker           VARCHAR NOT NULL,   -- 'points_against' | 'points_for' | 'commissioner'
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**Confidence:** HIGH — directly mirrors the data pattern in existing tables.

### Pattern 2: Rule-Dispatching `expected_draft_slot()`

**What:** Replace the current single-algorithm `expected_draft_slot()` in `pick_engine.py` with a dispatcher that branches on `non_playoff_basis`.

**Current function signature (to replace):**
```python
# backend/src/fantasy/picks/pick_engine.py line 35
def expected_draft_slot(win_pct: float, remaining_games: int, league_size: int) -> float:
```

**New dispatcher approach:**
```python
def expected_draft_slot_inverse(win_pct: float, remaining_games: int, league_size: int) -> float:
    # existing logic, unchanged

def expected_draft_slot_max_pf(points_for: float, league_max_pf: float, league_size: int) -> float:
    # ranks by points_for descending; lower PF = better (earlier) draft slot
    # slot = round((1 - points_for / max(league_max_pf, 1)) * (league_size - 1)) + 1

def expected_draft_slot(
    rule: LeagueDraftOrderRule | None,
    win_pct: float,
    remaining_games: int,
    league_size: int,
    points_for: float = 0.0,
    league_max_pf: float = 0.0,
) -> float | None:
    if rule is None:
        return None   # blocked state — D-01
    if rule.non_playoff_basis == NonPlayoffOrderBasis.INVERSE_STANDINGS:
        return expected_draft_slot_inverse(win_pct, remaining_games, league_size)
    if rule.non_playoff_basis == NonPlayoffOrderBasis.MAX_POINTS_FOR:
        return expected_draft_slot_max_pf(points_for, league_max_pf, league_size)
    return None
```

**Confidence:** HIGH — logically derived from D-07/D-08, code structure confirmed by reading `pick_engine.py`.

### Pattern 3: `PickValuationContext` Extension

**What:** Add `draft_order_rule: LeagueDraftOrderRule | None` to `PickValuationContext`. Add `rule_citation: str | None` to `PickValue`.

**Why inject via context rather than load in repo:** Consistent with how `class_strength_signal` was added (Phase 7 hook pattern). The engine receives all context as a typed model; it does not query the DB directly.

**PickValuationContext addition:**
```python
# backend/src/fantasy/picks/models.py
draft_order_rule: LeagueDraftOrderRule | None = Field(
    default=None,
    description="Phase 10: rule-aware slot projection. None = blocked state."
)
```

**PickValue addition:**
```python
rule_citation: str | None = Field(
    default=None,
    description=(
        "Backend-rendered citation string, e.g. 'Using: Max points for · Playoff teams by finish'. "
        "None = rule not configured; frontend renders blocked state."
    )
)
```

**Confidence:** HIGH — directly follows the existing Phase 7 hook pattern in `models.py`.

### Pattern 4: Rule Citation Rendering

**What:** Backend renders the full `rule_citation` string in `_compute_with_context()`. Frontend never assembles the string from raw fields.

**Rationale:** Per UI-SPEC implementation note 5: "The backend renders the full citation string... The frontend does not assemble this string from raw rule fields — it receives the pre-rendered string in the `rule_citation` field of `PickValue`."

**Backend rendering (in `_compute_with_context`):**
```python
rule_citation = _build_rule_citation(context.draft_order_rule)

def _build_rule_citation(rule: LeagueDraftOrderRule | None) -> str | None:
    if rule is None:
        return None
    basis_label = {
        NonPlayoffOrderBasis.INVERSE_STANDINGS: "Inverse standings",
        NonPlayoffOrderBasis.MAX_POINTS_FOR:    "Max points for",
    }[rule.non_playoff_basis]
    playoff_label = {
        PlayoffOrdering.BY_FINISH:      "Playoff teams by finish",
        PlayoffOrdering.BY_RECORD:      "Playoff teams by record",
        PlayoffOrdering.BY_POINTS_FOR:  "Playoff teams by points for",
    }[rule.playoff_ordering]
    return f"Using: {basis_label} · {playoff_label}"
```

**Confidence:** HIGH — per UI-SPEC §Copywriting Contract (confirmed citation template).

### Pattern 5: Schema Triple-Management

**This is a known pitfall in this codebase** (documented in STATE.md). New tables must be added in all three places:

1. `backend/alembic/versions/012_draft_order_rules.py` — Alembic migration
2. `backend/src/fantasy/startup_tasks.py` `_SCHEMA_COMPAT_TABLES` dict — runtime compat shim
3. `backend/tests/conftest.py` `SCHEMA_SQL` list — test schema

Omitting any one of the three causes silent test failures or missing tables in production.

**Confidence:** HIGH — explicitly documented in STATE.md §Blockers/Concerns and verified in `startup_tasks.py` lines 18–76 and `conftest.py`.

### Pattern 6: `PickRepo` Draft Order Rule CRUD

**What:** Add two methods to `PickRepo` following the same `get_/save_` pattern already in the file.

```python
def get_draft_order_rule(self, league_id: str) -> LeagueDraftOrderRule | None:
    row = self._conn.execute(
        "SELECT non_playoff_basis, playoff_ordering, tiebreaker "
        "FROM league_draft_order_rules WHERE league_id = ? LIMIT 1",
        [league_id],
    ).fetchone()
    if row is None:
        return None
    return LeagueDraftOrderRule(
        non_playoff_basis=row[0],
        playoff_ordering=row[1],
        tiebreaker=row[2],
    )

def save_draft_order_rule(self, league_id: str, rule: LeagueDraftOrderRule) -> None:
    # DuckDB upsert on UNIQUE league_id
    self._conn.execute(
        """
        INSERT INTO league_draft_order_rules (league_id, non_playoff_basis, playoff_ordering, tiebreaker)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (league_id) DO UPDATE SET
            non_playoff_basis = EXCLUDED.non_playoff_basis,
            playoff_ordering  = EXCLUDED.playoff_ordering,
            tiebreaker        = EXCLUDED.tiebreaker,
            updated_at        = CURRENT_TIMESTAMP
        """,
        [league_id, rule.non_playoff_basis.value, rule.playoff_ordering.value, rule.tiebreaker.value],
    )
```

**Confidence:** HIGH — mirrors `upsert_league` pattern in `LeagueRepo` and `save_pick_values` in `PickRepo`.

### Pattern 7: `_build_context()` Extension in `PickEngine`

**What:** Load the rule in `_build_context()` and inject it into `PickValuationContext`.

```python
def _build_context(self, pick, league_id, target_manager_id=None) -> PickValuationContext:
    draft_order_rule = self._repo.get_draft_order_rule(league_id)  # new
    class_strength_signal = self._load_class_strength_signal(league_id)
    demand_factor = ...
    return PickValuationContext(
        pick=pick,
        league_id=league_id,
        draft_order_rule=draft_order_rule,   # new
        class_strength_signal=class_strength_signal,
        target_manager_demand_factor=demand_factor,
    )
```

**Confidence:** HIGH — natural extension of existing `_build_context` at line 176.

### Pattern 8: Blocked Pick State in `_compute_with_context()`

**What:** When `context.draft_order_rule is None`, return a `PickValue` with `rule_citation=None`. The `expected_draft_slot` field becomes sentinel-safe.

**Key consideration:** `PickValue.expected_draft_slot` has `ge=1.0` validation. When the rule is absent, the engine must not call `expected_draft_slot()` at all. One approach: use a sentinel `expected_draft_slot=1.0` with `rule_citation=None` to signal the blocked state. The frontend detects `rule_citation is None` (not the slot value) to determine the blocked state.

**Confidence:** HIGH — constraint visible in `models.py` line 77; sentinel approach avoids Pydantic validation failure.

### Pattern 9: Frontend RuleCitation Component

**What:** `src/components/picks/RuleCitation.tsx` — shared component, props `{ citation: string | null, leagueId: string }`.

**Configured state:** `<Link to="/league/$leagueId" params={{leagueId}} hash="draft-order-rule" className="text-xs text-muted-foreground mt-1">"Using: ..."</Link>`

**Unconfigured state:** `<Link ... className="text-xs text-primary underline cursor-pointer mt-1">"Rule not configured — tap to set up"</Link>`

**Blocked chip state:** When `citation === null`, `AssetChip` pick variant suppresses `TimingBadge` and `timing_reasoning` per UI-SPEC implementation note 3.

**Confidence:** HIGH — per UI-SPEC §RuleCitation and implementation notes 2–3.

### Anti-Patterns to Avoid

- **Silent inverse-standings fallback:** `expected_draft_slot()` MUST return `None` when rule is absent, not silently compute an inverse-standings value. D-01 is explicit.
- **Frontend string assembly:** The frontend MUST NOT build the citation string from raw rule fields. Backend renders it per UI-SPEC implementation note 5.
- **Schema in only one place:** New `league_draft_order_rules` table must appear in migration, `startup_tasks.py`, AND `conftest.py`. Missing any one causes silent failures (STATE.md blocker).
- **Wizard/stepper UI:** Single-page form only per D-10. No multi-step flow.
- **Per-surface citation logic:** All surfaces use the shared `RuleCitation` component — never inline the citation logic in `LeaguePickList`, `AssetChip`, or `EvaluationOutputPanel`.
- **PickValue validation bypass:** Do not change `expected_draft_slot: float = Field(ge=1.0)` to optional — use a sentinel value (1.0) alongside `rule_citation=None` to signal blocked state without breaking the model.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 2-option form selection | Custom toggle/checkbox | shadcn `RadioGroup` + `RadioGroupItem` | Already decided in UI-SPEC; consistent with other form patterns |
| 3-option dropdowns | Custom dropdown | shadcn `Select` | Already in use across the project |
| Rule persistence | In-memory state | `league_draft_order_rules` table + `PickRepo.save_draft_order_rule()` | Must survive restarts; matches all other league-scoped data |
| Citation format | `switch` statements in every surface | `_build_rule_citation()` in `pick_engine.py` + `RuleCitation.tsx` | Single source of truth; backend renders, frontend consumes |
| Cache invalidation after rule save | Manual refetch per component | `queryClient.invalidateQueries({ queryKey: ['picks', leagueId] })` | TanStack Query handles propagation to all subscribed components |

---

## Common Pitfalls

### 1. Schema Triple-Management Gap (HIGH RISK)
**Pitfall:** Adding `league_draft_order_rules` to the Alembic migration but not to `startup_tasks.py _SCHEMA_COMPAT_TABLES` and `conftest.py SCHEMA_SQL`.
**Effect:** Tests pass against conftest schema, dev server crashes on startup with table-not-found; or vice versa.
**Prevention:** The plan must have a dedicated step that adds the DDL to all three locations atomically.
**Evidence:** STATE.md §Blockers/Concerns; verified in `startup_tasks.py` lines 18–76.

### 2. Pydantic `ge=1.0` on `expected_draft_slot`
**Pitfall:** Returning `expected_draft_slot=0` or `None` when rule is absent; Pydantic raises a validation error.
**Effect:** The `/picks/{league_id}` endpoint 500s for any league without a rule configured.
**Prevention:** Use sentinel value `1.0` when rule is absent; frontend detects blocked state from `rule_citation=None`, not the slot value.
**Evidence:** `PickValue` model in `backend/src/fantasy/picks/models.py` line 77.

### 3. `_build_context()` DB hit on every pick in batch
**Pitfall:** `get_draft_order_rule()` called once per pick in `compute_batch()` via `_build_context()`.
**Effect:** N DB queries for N picks where one would suffice.
**Prevention:** Load the rule once before the batch loop and pass it through `_build_context()` or directly into `PickValuationContext`.
**Evidence:** `compute_batch()` in `pick_engine.py` lines 304–368 — `_build_context` is called per pick in the loop.

### 4. `points_for` Not Available in Current `standings` Query
**Pitfall:** `max_points_for` ordering requires `fpts` (points for) per roster, but `PickRepo.get_standings()` currently returns a `TeamStandingsRow` that includes `fpts` only indirectly via the `standings` table.
**Investigation:** `standings` table has `fpts FLOAT` (verified in `db/models.py` line 56). However, `TeamStandingsRow` in `picks/models.py` does not include `fpts`. The `max_points_for` slot projection needs `fpts` from the standings table plus the league-wide max `fpts`.
**Prevention:** Either extend `TeamStandingsRow` to include `fpts`, or compute max-PF slot in `PickRepo.get_draft_order_rule_context()` as a separate query that returns `{roster_id: slot}` ranked by fpts desc.
**Recommendation:** A separate `get_max_pf_slots(league_id) -> dict[int, int]` method in `PickRepo` is cleaner — ranks all rosters by `fpts` DESC, assigns slots 1..N, returns a dict for O(1) lookups. This avoids polluting `TeamStandingsRow`.
**Confidence:** HIGH — `fpts` column confirmed in `db/models.py`; absence from `TeamStandingsRow` confirmed in `picks/models.py`.

### 5. TanStack Router Hash Navigation
**Pitfall:** `<Link hash="draft-order-rule">` navigates to the league page but does not scroll to the form if TanStack Router's hash behavior is not configured.
**Prevention:** Add `id="draft-order-rule"` to the outer wrapper of `DraftOrderRuleForm` per UI-SPEC implementation note 7. Verify TanStack Router version supports `hash` prop on `<Link>` (it does in v1.x).
**Evidence:** UI-SPEC §Interaction States, implementation notes 7–8.

### 6. `PickValue.rule_citation` Breaks Existing Frontend `PickValue` Type
**Pitfall:** Adding `rule_citation: string | null` to the backend `PickValue` model without updating the TypeScript `PickValue` interface in `frontend/src/api/types.ts` causes TypeScript errors on all surfaces that destructure `PickValue`.
**Prevention:** The plan must update `PickValue` in `types.ts` in the same plan as the backend model change.
**Evidence:** `frontend/src/api/types.ts` lines 203–221; all pick surfaces import this type.

### 7. Confirmed-Slot Bypass
**Pitfall:** The confirmed-slot path (`confirmed_slot is not None`) in `_compute_with_context()` skips `expected_draft_slot()` and sets `slot = float(confirmed_slot)` directly (line 221–222). This path also needs a valid `rule_citation` even though the rule was not used for slot projection.
**Prevention:** Render `rule_citation` from the rule regardless of whether the slot came from projection or confirmed slot. The citation describes the league's ordering rule, not how the current slot was derived.
**Evidence:** `pick_engine.py` lines 221–228.

---

## Code Examples

### Enum Definitions (constants.py)
```python
# backend/src/fantasy/picks/constants.py
from enum import Enum

class NonPlayoffOrderBasis(str, Enum):
    INVERSE_STANDINGS = "inverse_standings"
    MAX_POINTS_FOR    = "max_points_for"

class PlayoffOrdering(str, Enum):
    BY_FINISH     = "by_finish"
    BY_RECORD     = "by_record"
    BY_POINTS_FOR = "by_points_for"

class DraftTiebreaker(str, Enum):
    POINTS_AGAINST = "points_against"
    POINTS_FOR     = "points_for"
    COMMISSIONER   = "commissioner"
```

### LeagueDraftOrderRule Model (models.py)
```python
# backend/src/fantasy/picks/models.py
class LeagueDraftOrderRule(BaseModel):
    model_config = ConfigDict(frozen=False)

    non_playoff_basis: NonPlayoffOrderBasis
    playoff_ordering: PlayoffOrdering
    tiebreaker: DraftTiebreaker

    def is_fully_configured(self) -> bool:
        return True   # all fields required at construction; None rule = unconfigured
```

### Max-PF Slot Computation
```python
# backend/src/fantasy/picks/pick_engine.py (new function)
def expected_draft_slot_max_pf(
    points_for: float,
    max_pf_slots: dict[int, int],   # roster_id -> rank (1 = worst record = pick 1)
    roster_id: int,
    league_size: int,
) -> float:
    """Return projected draft slot using max-PF ordering.

    Lower PF = earlier pick (non-playoff teams ranked worst-to-best by PF).
    Slot is pre-computed by PickRepo.get_max_pf_slots() to ensure correct
    relative ranking across all rosters.
    """
    return float(max_pf_slots.get(roster_id, (league_size + 1) // 2))
```

### New API Endpoint (leagues router)
```python
# backend/src/fantasy/routers/leagues.py (new file or extension)
from pydantic import BaseModel

class DraftOrderRuleRequest(BaseModel):
    non_playoff_basis: NonPlayoffOrderBasis
    playoff_ordering: PlayoffOrdering
    tiebreaker: DraftTiebreaker

@router.put("/leagues/{league_id}/draft-order-rule", response_model=DraftOrderRuleResponse)
def save_draft_order_rule(
    league_id: str,
    body: DraftOrderRuleRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> DraftOrderRuleResponse:
    rule = LeagueDraftOrderRule(**body.model_dump())
    PickRepo(conn).save_draft_order_rule(league_id, rule)
    return DraftOrderRuleResponse(league_id=league_id, rule=rule)

@router.get("/leagues/{league_id}/draft-order-rule", response_model=DraftOrderRuleResponse | None)
def get_draft_order_rule(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> DraftOrderRuleResponse | None:
    rule = PickRepo(conn).get_draft_order_rule(league_id)
    if rule is None:
        return None
    return DraftOrderRuleResponse(league_id=league_id, rule=rule)
```

### Frontend RuleCitation Component
```tsx
// frontend/src/components/picks/RuleCitation.tsx
import { Link } from "@tanstack/react-router"

export function RuleCitation({
  citation,
  leagueId,
}: {
  citation: string | null
  leagueId: string
}) {
  if (citation) {
    return (
      <Link
        to="/league/$leagueId"
        params={{ leagueId }}
        hash="draft-order-rule"
        className="mt-1 block text-xs text-muted-foreground"
      >
        {citation}
      </Link>
    )
  }
  return (
    <Link
      to="/league/$leagueId"
      params={{ leagueId }}
      hash="draft-order-rule"
      className="mt-1 block text-xs text-primary underline cursor-pointer"
    >
      Rule not configured — tap to set up
    </Link>
  )
}
```

---

## Validation Architecture

> Required for Nyquist Dim 8. Each major capability needs acceptance test coverage.

### 1. Slot Projection Algorithms — Unit Tests

**File:** `backend/tests/picks/test_pick_engine.py`

**What to verify:**
- `expected_draft_slot_inverse()`: Existing regression fixture passes (win_pct=0.0 → slot 1, win_pct=1.0 → slot N, win_pct=0.5 → slot mid).
- `expected_draft_slot_max_pf()`: New regression fixture — roster with lowest `fpts` gets slot 1, highest `fpts` gets slot N.
- Rule `None` → `expected_draft_slot()` returns `None` (blocked state).
- Both branches return `float` in range `[1.0, league_size]` for valid inputs.
- `PickValue.rule_citation` is `None` when rule is `None`.
- `PickValue.rule_citation` matches expected citation string when rule is configured.

**Regression fixtures required (per success criterion 5):**
```python
@pytest.mark.parametrize("scenario,win_pct,remaining,league_size,expected_slot_range", [
    ("inverse_standings_worst",  0.0, 0, 12, (1, 2)),    # worst record → pick 1 or 2
    ("inverse_standings_mid",    0.5, 0, 12, (6, 7)),    # 50% record → mid
    ("inverse_standings_best",   1.0, 0, 12, (11, 12)),  # best record → late pick
])
def test_inverse_standings_regression(scenario, win_pct, remaining, league_size, expected_slot_range):
    ...

@pytest.mark.parametrize("scenario,roster_fpts,all_fpts,league_size,expected_slot", [
    ("max_pf_worst",  100.0, [200, 180, 160, 140, 120, 100], 6, 1),  # lowest PF → pick 1
    ("max_pf_best",   200.0, [200, 180, 160, 140, 120, 100], 6, 6),  # highest PF → pick 6
    ("max_pf_mid",    160.0, [200, 180, 160, 140, 120, 100], 6, 3),  # mid PF → mid slot
])
def test_max_pf_regression(scenario, roster_fpts, all_fpts, league_size, expected_slot):
    ...
```

### 2. Draft Order Rule CRUD — Unit Tests

**File:** `backend/tests/picks/test_pick_repo.py`

**What to verify:**
- `save_draft_order_rule()` inserts a new row for a league with no prior rule.
- `save_draft_order_rule()` upserts (overwrites) an existing rule.
- `get_draft_order_rule()` returns `None` for an unconfigured league.
- `get_draft_order_rule()` returns the correct `LeagueDraftOrderRule` after save.
- All three enum fields round-trip correctly through DuckDB VARCHAR storage.

### 3. Blocked State — Integration Tests

**File:** `backend/tests/integration/test_pick_router.py`

**What to verify:**
- `GET /picks/{league_id}` with no rule configured returns picks with `rule_citation: null`.
- `GET /picks/{league_id}` with no rule does NOT return `expected_draft_slot` values derived from inverse-standings (i.e., does not silently fall back — verify by confirming all returned picks have a sentinel `expected_draft_slot` of `1.0`).
- `GET /picks/{league_id}` after rule configuration returns picks with non-null `rule_citation` matching the expected citation format.
- `PUT /leagues/{league_id}/draft-order-rule` returns 200 and the saved rule fields.
- `GET /leagues/{league_id}/draft-order-rule` returns `null` (HTTP 200 with null body) for unconfigured league.

### 4. Rule Citation Format — Unit Tests

**File:** `backend/tests/picks/test_pick_engine.py`

**What to verify:**
- `_build_rule_citation(None)` returns `None`.
- `_build_rule_citation(rule with inverse_standings + by_finish)` returns `"Using: Inverse standings · Playoff teams by finish"`.
- `_build_rule_citation(rule with max_points_for + by_record)` returns `"Using: Max points for · Playoff teams by record"`.
- All 6 valid combinations (2 bases × 3 playoff orderings) produce the expected string without raising.

### 5. Schema Triple-Management — Integration Test

**File:** `backend/tests/test_startup_tasks.py`

**What to verify:**
- `ensure_runtime_schema()` creates `league_draft_order_rules` when the table does not exist.
- After `ensure_runtime_schema()`, `GET /leagues/{id}/draft-order-rule` does not raise a table-not-found error.

### 6. Frontend RuleCitation — No Automated Tests Required

The `RuleCitation` component is stateless (no side effects beyond navigation). Manual verification during frontend plan execution is sufficient. The component contract (props and rendered output) is covered by the integration tests that verify `rule_citation` appears in API responses.

### 7. Confirmed-Slot + Rule Citation — Unit Test

**What to verify:**
- A pick with a confirmed slot still gets a non-null `rule_citation` when the rule is configured (citation describes the rule, not how the slot was derived).
- A pick with a confirmed slot AND no rule configured still gets `rule_citation: None`.

---

## Recommended Plan Structure

Based on the research above, the phase cleanly decomposes into four plans:

| Plan | Scope | Key Deliverables |
|------|-------|-----------------|
| 10-01 | Backend model + DB | `LeagueDraftOrderRule` model/enums, migration 012, `startup_tasks` + `conftest` updates, `PickRepo` CRUD methods, league router GET/PUT endpoints |
| 10-02 | Pick engine integration | `expected_draft_slot` dispatcher (inverse + max-PF), `_build_context` extension, `_compute_with_context` blocked state + citation rendering, `PickValue.rule_citation` field, `max_pf_slots` query |
| 10-03 | Backend tests + regression fixtures | Unit tests for both algorithms, CRUD tests, blocked-state integration tests, citation format tests |
| 10-04 | Frontend | `RuleCitation.tsx`, `DraftOrderRuleForm` in `league.$leagueId.tsx`, `PickValue` type update, `queries.ts` additions, citation added to `LeaguePickList`, `AssetChip`, `EvaluationOutputPanel`, draft room pick displays |

---

## Runtime State Inventory

> This is an enhancement phase, not a rename/refactor. No stored data requires migration or transformation. The `league_draft_order_rules` table is new; all existing rows in existing tables are unaffected.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | No existing `league_draft_order_rules` rows — table is new | None; table created by migration 012 |
| Live service config | Existing `pick_values` rows computed without a rule | Rows remain valid; they will get `rule_citation=null` on next recompute after rule is configured |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |
