# Phase 11 Research: Roster & Lineup Intelligence

**Generated:** 2026-03-24
**Phase:** 11-roster-lineup-intelligence
**Confidence levels:** HIGH = verified in codebase/official docs, MEDIUM = verified pattern in codebase, LOW = reasoned from context

---

## User Constraints

### Locked Decisions (Planner MUST honor these verbatim)

**Replacement-level definition**
- D-01: Replacement level is computed per-league from actual roster data — no global ADP baseline.
- D-02: The replacement player at each position is the weakest starter at that position across all teams in the league (not the waiver wire).
- D-03: Flex slots use the best available player regardless of position — no position-specific replacement for flex.
- D-04: Replacement level is dynamic — recomputed on each ingest cycle.

**Title-window score**
- D-05: Title-window is expressed as a label, not a numeric score. Labels are: "Peak Window", "Fading Window", "Outside Window".
- D-06: Starter ceiling is the primary weight — a team with two elite WR1s and a top-5 QB scores higher than a team with broad depth and no ceiling pieces.
- D-07: Title-window label lives in a separate panel/card from the existing scorecard — visually distinct, not a 10th scorecard dimension.
- D-08: Title-window label feeds back into the direction label engine — a high win_now scorecard combined with an "Outside Window" title-window label nudges toward `fragile_contender` or similar; exact integration point is Claude's discretion.
- D-09: Title-window panel is visible on every team screen (league drill-in).

**Roster hygiene panel**
- D-10: Consolidate and cut get top billing — most-used action types; stash and move-to-taxi are present but secondary.
- D-11: Cut candidates are evaluated on two criteria: primary being roster slot constraint ("this spot is blocking a better move") and secondary being low upside; the slot-blocking framing should appear in the suggestion reasoning.
- D-12: Consolidation suggestions directly reference the trade evaluator — each suggestion names specific players to package and a specific target from a named counterparty (e.g., "Package Player A + Player B → target Player X from Manager Y").
- D-13: Up to 5 suggestions per action type.
- D-14: Suggestions reference `TradeEngine` / `PackageBuilder` output where available — no standalone consolidation engine; reuse Phase 5 infrastructure.

**Taxi / IR eligibility modeling**
- D-15: Taxi eligibility is configured per-league — a per-league taxi configuration block is required (similar to `LeagueDraftOrderRule` from Phase 10).
- D-16: IR state is reflected from Sleeper as-is — no IR move recommendations.
- D-17: Manual exceptions are kept simple — basic per-league taxi config is sufficient.
- D-18: Taxi/IR occupancy is surfaced as a separate section from the roster hygiene panel — informational slot accounting only.

### Claude's Discretion Areas

- Exact label strings for title-window (confirmed as "Peak Window" / "Fading Window" / "Outside Window" per D-05 and UI-SPEC).
- Weight formula for the title-window classifier (starter ceiling is primary; lineup stability and playoff-usable depth are secondary).
- How title-window feeds into `DirectionEngine` — via scorecard input augmentation or as a post-classification adjustment.
- Alembic migration numbering (must not conflict with 001–013 already in use — next available is 014).
- DB schema for per-league taxi configuration and lineup calculator outputs.
- Whether `LineupEngine` and `HygieneEngine` are separate classes or combined in an `IntelligenceService` extension.
- Exact threshold values that separate "Peak Window" / "Fading Window" / "Outside Window".

### Deferred Ideas (Out of Scope — Ignore)

- Weekly start/sit optimizer — dynasty-focused product; out of scope per REQUIREMENTS.md.
- IR move recommendations — user handles IR manually (D-16).
- Complex mid-season taxi eligibility overrides / house-rule exceptions (D-17).
- Waiver wire watchlist and bid-range suggestions — Phase 15 (FS-05).

---

## Standard Stack

Phase 11 adds no new dependencies. All implementation uses the existing project stack.

### Core (existing — confirmed in codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| DuckDB | 1.5.0 | Analytical queries for lineup and replacement-level calculations | Chosen in Phase 1; 10-17x faster than SQLite for cross-roster aggregations |
| FastAPI | current | New `/intelligence/lineup/{league_id}/{roster_id}` and `/leagues/{league_id}/taxi-config` routes | Existing router pattern |
| Pydantic v2 | current | `LineupResult`, `HygieneSuggestion`, `TitleWindowResult`, `TaxiConfig` domain models | All domain models use Pydantic v2 `BaseModel` |
| Python 3.12 | 3.12 | All engine classes | Project-wide |

### Supporting (existing — confirmed in codebase)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fantasy.trade.package_builder.PackageBuilder` | internal | Generates named consolidation suggestions with counterparty context | Reuse for D-12/D-14; do not build a new recommender |
| `fantasy.intelligence.scorecard_engine.ScorecardEngine` | internal | Already reads starters/bench/taxi/ir/roster_positions from DB | LineupEngine consumes same `ScorecardInputs` model |
| `fantasy.intelligence.direction_engine.DirectionEngine` | internal | `classify()` feeds back title-window result via augmentation | Title-window integration point |
| `fantasy.intelligence.valuation_engine.ValuationEngine` | internal | `comp_ceiling` field on `PlayerValue` is the ceiling signal | Title-window classifier reads this directly |
| React 19 / TanStack Query | current | Frontend query/mutation for new endpoints | `queryOptions` + `useMutation` pattern in `queries.ts` |
| shadcn (manual pattern) | N/A | Component library in `frontend/src/components/ui/` | All new components follow this pattern |

**Installation:** No new packages required.

---

## Architecture Patterns

### Established Pattern: Per-League Config Model (HIGH confidence)

Phase 10 established `LeagueDraftOrderRule` as the canonical pattern for per-league configuration blocks. Phase 11's taxi config follows this exactly.

Source: `/Users/jakyeamos/Desktop/Fantasy/backend/alembic/versions/013_draft_order_rules.py` and `/Users/jakyeamos/Desktop/Fantasy/backend/src/fantasy/picks/models.py`

**Pattern:**
```python
# Model (in new models.py or picks/models.py equivalent)
class LeagueTaxiConfig(BaseModel):
    model_config = ConfigDict(frozen=False)
    taxi_slots: int          # total taxi roster slots
    taxi_years_eligible: int # years a player can remain on taxi (commonly 1-2)
    years_pro_cutoff: int    # years of NFL experience that disqualifies taxi eligibility

# DB table (migration 014_taxi_config.py)
CREATE TABLE IF NOT EXISTS league_taxi_configs (
    id          INTEGER PRIMARY KEY,
    league_id   VARCHAR NOT NULL UNIQUE,
    taxi_slots  INTEGER NOT NULL,
    taxi_years_eligible INTEGER NOT NULL,
    years_pro_cutoff    INTEGER NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)

# Router endpoint pattern: /leagues/{league_id}/taxi-config
# GET returns current config (null if not configured)
# PUT saves config
```

### Established Pattern: Engine Isolation via IntelligenceService (HIGH confidence)

Each engine (`ScorecardEngine`, `DirectionEngine`, `ValuationEngine`) is a separate class injected into `IntelligenceService`. `LineupEngine` and `HygieneEngine` follow the same pattern.

Source: `/Users/jakyeamos/Desktop/Fantasy/backend/src/fantasy/intelligence/intelligence_service.py` lines 14-19

```python
class IntelligenceService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._scorecard_engine = ScorecardEngine(conn)
        self._direction_engine = DirectionEngine()
        self._valuation_engine = ValuationEngine(conn)
        # Phase 11 adds:
        self._lineup_engine = LineupEngine(conn)
        self._hygiene_engine = HygieneEngine(conn)
```

`compute_league()` is extended to call `LineupEngine.compute()` and `HygieneEngine.compute()` after scorecards/directions/values, persisting results.

### Established Pattern: Schema Triple-Write (HIGH confidence — CRITICAL)

Three places must be updated for every new table:
1. Alembic migration (`backend/alembic/versions/NNN_name.py`)
2. `startup_tasks.py` `_SCHEMA_COMPAT_TABLES` dict (runtime compat shim)
3. `backend/tests/conftest.py` `SCHEMA_SQL` list (test fixture)

Source: `/Users/jakyeamos/Desktop/Fantasy/backend/src/fantasy/startup_tasks.py` lines 18-97, `/Users/jakyeamos/Desktop/Fantasy/backend/tests/conftest.py` lines 7-336

Missing any of the three causes silent failures in production or tests. Migration 014 creates `league_taxi_configs`; migration 015 creates `lineup_scores`; migration 016 creates `hygiene_suggestions`. All three must also appear in `startup_tasks.py` and `conftest.py`.

### Pattern: Replacement-Level Computation (HIGH confidence)

Source: ScorecardEngine pattern at `/Users/jakyeamos/Desktop/Fantasy/backend/src/fantasy/intelligence/scorecard_engine.py` lines 34-91. The engine already loads all rosters in the league via `compute_all()` and passes the full `all_inputs: dict[int, ScorecardInputs]` to each scoring method.

`LineupEngine.compute_all()` follows the same two-pass pattern:
1. First pass: gather `ScorecardInputs` for all rosters in the league.
2. Compute replacement level per position: for each position P, find the minimum `_value_proxy(inputs, player_id)` across all starters at position P across all rosters.
3. Second pass: for each roster, score each starter slot against its positional replacement level.

**Flex slot handling (D-03):** When the lineup slot is FLEX or SUPER_FLEX, the replacement baseline is the minimum value among all players starting in any FLEX/SUPER_FLEX slot across the league (regardless of position).

### Pattern: Title-Window Classifier (MEDIUM confidence — logic reasoned from codebase)

`TitleWindowClassifier` takes a roster's lineup scores and player values and produces one of three labels.

Primary weight: `comp_ceiling` from `PlayerValue` (already computed by `ValuationEngine`). Secondary weights: lineup stability (inverse of `fragility` scorecard dimension), playoff-usable depth (bench player count above a value threshold).

**Threshold design:** Use percentile buckets within the league rather than global fixed thresholds. This makes labels meaningful relative to this league's competition level.

```python
TITLE_WINDOW_LABELS = Literal["Peak Window", "Fading Window", "Outside Window"]

def classify_title_window(
    ceiling_score: float,   # normalized 0-1 within league
    stability_score: float, # normalized 0-1 within league
    depth_score: float,     # normalized 0-1 within league
) -> str:
    composite = 0.60 * ceiling_score + 0.25 * stability_score + 0.15 * depth_score
    if composite >= 0.65:
        return "Peak Window"
    if composite >= 0.35:
        return "Fading Window"
    return "Outside Window"
```

**Direction integration (D-08):** The cleanest integration point — post-classification adjustment in `DirectionEngine.classify()`. After the primary label is determined, if title-window is "Outside Window" and primary_label is in `CONTENDER_DIRECTION_LABELS`, nudge toward `fragile_contender` by injecting a synthetic `fragility` boost before the final label selection. This avoids touching `DIRECTION_WEIGHTS` and is reversible.

### Pattern: HygieneEngine Consolidation Suggestions (HIGH confidence)

Source: `/Users/jakyeamos/Desktop/Fantasy/backend/src/fantasy/trade/package_builder.py`

`HygieneEngine` does not build its own package recommender. For consolidation suggestions (D-14), it:
1. Queries `player_values` for the roster — identifies the bottom-value players by lens_direction.
2. Queries all other rosters for positional needs (existing `positional_needs` field in `roster_summary` on manager profiles).
3. Builds a `TradeRequest` with the consolidation package and calls `PackageBuilder.build()`.
4. Surfaces the result as a `HygieneSuggestion` with action type `"consolidate"`, named counterparty, and a link to pre-fill the trade evaluator.

For cut candidates (D-11): primary criterion is roster slot utilization — players below a value floor who occupy a non-IR/taxi slot. Reasoning leads with the slot-blocking framing per D-11.

### Pattern: FastAPI Router Extension (HIGH confidence)

New endpoints follow the existing `/intelligence` router pattern. Two options:
- Extend `/intelligence` router with sub-routes: `GET /intelligence/lineup/{league_id}/{roster_id}` and `GET /intelligence/hygiene/{league_id}/{roster_id}`
- Add a new router `/leagues` for taxi config: `GET /leagues/{league_id}/taxi-config` and `PUT /leagues/{league_id}/taxi-config`

The taxi config route uses `get_write_db_conn` for PUT (same as draft order rule pattern) and `get_read_db_conn` for GET.

### Pattern: Frontend Query and Mutation (HIGH confidence)

Source: `/Users/jakyeamos/Desktop/Fantasy/frontend/src/api/queries.ts` — `draftOrderRuleOptions` and `saveDraftOrderRule` are the direct template.

```typescript
// GET query option
export const lineupScoreOptions = (leagueId: string, rosterId: number) =>
  queryOptions({
    queryKey: ["intelligence", "lineup", leagueId, rosterId],
    queryFn: () => getJson<LineupResult>(`/intelligence/lineup/${leagueId}/${rosterId}`),
    staleTime: 5 * 60 * 1000,
    enabled: leagueId.trim().length > 0 && rosterId > 0,
  })

// PUT mutation for taxi config (same pattern as saveDraftOrderRule)
export async function saveTaxiConfig(
  leagueId: string,
  config: LeagueTaxiConfig,
): Promise<TaxiConfigResponse> { ... }
```

New types go in `frontend/src/api/types.ts` following the existing interface pattern.

### Pattern: UI Component Placement (HIGH confidence)

Source: `/Users/jakyeamos/Desktop/Fantasy/.planning/phases/11-roster-lineup-intelligence/11-UI-SPEC.md`

Panel insertion order in `league.$leagueId.tsx` (top to bottom):
1. TitleWindowPanel — full-width card, below existing direction header card
2. LineupStrengthCard — full-width card, below TitleWindowPanel
3. RosterHygienePanel — full-width card, below LineupStrengthCard
4. TaxiIRSlotSummary + TaxiConfigForm — combined card, bottom of stack

New component directories: `frontend/src/components/lineup/` and `frontend/src/components/hygiene/`.

### Anti-Patterns to Avoid

- **Building a standalone consolidation recommender:** `PackageBuilder` already generates specific named packages from manager profiles. Use it directly (D-14).
- **Global ADP replacement level:** Replacement level must be computed per-league from actual starters (D-01/D-02), not from any global ADP table.
- **Title-window as a 10th scorecard dimension:** It must be a separate classification with its own label and panel (D-07). Do not add it to `TeamScorecard.as_dict()`.
- **IR recommendations:** Do not suggest IR moves. IR state is read-only from Sleeper (D-16).
- **Missing schema triple-write:** Every new table must be added to Alembic migration, `startup_tasks.py`, and `conftest.py`. Missing any one causes silent failures.
- **Hardcoded taxi eligibility:** Taxi rules vary by league; configuration must be per-league (D-15), not derived from Sleeper defaults.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Named consolidation suggestions with counterparty context | Custom recommender engine | `PackageBuilder.build()` (Phase 5) | Already integrates manager profiles and pitch angles; building a duplicate wastes implementation and creates divergence |
| Player ceiling signal | New ceiling computation | `PlayerValue.comp_ceiling` from `ValuationEngine` | Already computed per-league-per-direction and stored in `player_values` table |
| Roster slot inventory | Manual slot parsing | `ScorecardInputs.roster_positions`, `starters`, `bench`, `taxi`, `ir` | Already loaded and validated by `ScorecardEngine._gather_inputs()` |
| Per-league config CRUD | Custom storage layer | Pattern from `LeagueDraftOrderRule` + `PickRepo.save_draft_order_rule()` | The exact CRUD pattern is proven and testable in 30 lines |
| Player value proxies | New value computation | `ScorecardEngine._value_proxy()` and `ValuationEngine.compute_all()` | Both already exist; lineup engine should use the same value signals for consistency |

**Key insight:** Phase 11 is an assembly phase, not a from-scratch phase. LineupEngine reads `ScorecardInputs` (already populated), calls ValuationEngine signals, and packages the output. HygieneEngine calls PackageBuilder. The only net-new logic is the replacement-level computation, the title-window classifier, and the hygiene scoring heuristics.

---

## Common Pitfalls

### Pitfall 1: Schema Triple-Write Omission (HIGH risk)
The project has three independent schema copies: Alembic, `startup_tasks.py`, and `conftest.py`. Every phase since 6 has required updating all three. Missing any causes silent test passes but runtime failures. Phase 11 adds 3 new tables (taxi config, lineup scores, hygiene suggestions) — all three must appear in all three places.

### Pitfall 2: Migration Number Collision (HIGH risk)
Migrations 001–013 are in use. Next available is 014. Confirm the current maximum in `backend/alembic/versions/` before assigning numbers. Phase 11 needs 3 migrations: 014, 015, 016 (or packaged as fewer if tables can be logically grouped).

### Pitfall 3: Replacement Level Edge Cases (MEDIUM risk)
- A position with only one starter across the entire league (e.g., TE in small leagues): replacement level equals that player's value, making their starter score 0. Need a floor — fallback to position median from `position_medians` on `ScorecardInputs`.
- A roster with empty starter slots (injured player left in slot as "0"): SleeperMapper already filters out `"0"` values in `_valid_player_ids`, but confirm this covers the lineup calculator's view.
- Leagues with SUPER_FLEX: replacement level for SUPER_FLEX slot must use the best-available-across-positions baseline (D-03), not a QB-specific baseline.

### Pitfall 4: Title-Window Direction Integration Coupling (MEDIUM risk)
The direction engine is stateless and pure (`classify(scorecard: TeamScorecard) -> DirectionResult`). Injecting a title-window nudge cannot happen inside `DirectionEngine.classify()` without changing its signature or making it non-pure. The correct approach is to augment `ScorecardInputs` before passing to `ScorecardEngine` (upstream) or to apply a post-classification label swap in `IntelligenceService.compute_league()` (downstream). The downstream approach is safer and does not affect scorecard numeric values.

### Pitfall 5: HygieneEngine Calling PackageBuilder Per-Roster Cost (LOW risk)
`PackageBuilder.build()` calls `TradeRepo.get_manager_profile()` and `TradeRepo.get_pitch_angles()` per suggestion. For a league with 12 rosters and 5 consolidation suggestions each, this is 60+ DB queries. Use a pre-fetched profile cache dictionary inside `HygieneEngine.compute_all()` and pass it through to avoid N+1 DB calls.

### Pitfall 6: Frontend Query Invalidation After Taxi Config Save (MEDIUM risk)
Saving the taxi config should invalidate lineup score and hygiene queries (same pattern as draft order rule saving invalidating pick queries). Failure to invalidate means the UI shows stale data that does not reflect the new config. Pattern: `queryClient.invalidateQueries({ queryKey: ["intelligence", "lineup", leagueId] })` and `queryClient.invalidateQueries({ queryKey: ["intelligence", "hygiene", leagueId] })` in the `onSuccess` callback.

### Pitfall 7: Stash vs. Taxi Suggestion Confusion (LOW risk)
"Stash" (keep on bench, speculative hold) and "Move to Taxi" (eligible player who should be on taxi) are different actions with different eligibility logic. Stash is a value judgment (young player worth holding). Taxi is an eligibility + slot-efficiency judgment (player qualifies for taxi and should occupy that slot to free a bench spot). Do not conflate them in the hygiene scoring logic.

---

## Code Examples

### Example 1: Replacement Level Computation

```python
# LineupEngine._compute_replacement_levels(
#     all_inputs: dict[int, ScorecardInputs],
#     position: str
# ) -> float
def _compute_replacement_level(
    self,
    all_inputs: dict[int, ScorecardInputs],
    position: str,
) -> float:
    """
    Replacement level = weakest starter at this position across all rosters in the league.
    Falls back to position median if no starters found at this position.
    """
    starter_values = []
    for inputs in all_inputs.values():
        for player_id in inputs.starters:
            player_pos = inputs.player_positions.get(player_id, "UNKNOWN")
            if player_pos == position:
                starter_values.append(self._value_proxy(inputs, player_id))
    if not starter_values:
        # fallback: use position median from any roster's position_medians
        first_inputs = next(iter(all_inputs.values()))
        return float(first_inputs.position_medians.get(position, 5.0))
    return min(starter_values)
```

### Example 2: Title-Window Classification with League-Normalized Inputs

```python
# After computing lineup scores for all rosters in the league,
# normalize ceiling_scores within the league before classifying.
# This makes "Peak Window" meaningful relative to this league.

ceiling_raw = {
    roster_id: max(
        (inputs.player_values.get(pid, {}).get("comp_ceiling", 0.0) or 0.0)
        for pid in inputs.starters
    )
    for roster_id, inputs in all_inputs.items()
}
ceiling_normalized = normalize_within_league(ceiling_raw)  # existing helper in scorecard_engine.py

PEAK_WINDOW_THRESHOLD = 0.65
FADING_WINDOW_THRESHOLD = 0.35

def _classify_title_window(composite: float) -> str:
    if composite >= PEAK_WINDOW_THRESHOLD:
        return "Peak Window"
    if composite >= FADING_WINDOW_THRESHOLD:
        return "Fading Window"
    return "Outside Window"
```

### Example 3: Direction Post-Classification Adjustment (D-08)

```python
# In IntelligenceService.compute_league(), after classify():
for roster_id, direction in directions.items():
    lineup_result = lineup_results.get(roster_id)
    if lineup_result and lineup_result.title_window_label == "Outside Window":
        if direction.primary_label in CONTENDER_DIRECTION_LABELS:
            # Nudge: re-run classify with fragility boosted
            adjusted_scorecard = scorecards[roster_id].model_copy()
            adjusted_scorecard.fragility = min(1.0, adjusted_scorecard.fragility + 0.15)
            adjusted_direction = self._direction_engine.classify(adjusted_scorecard)
            # Only swap if the adjusted label differs
            if adjusted_direction.primary_label != direction.primary_label:
                directions[roster_id] = adjusted_direction
```

### Example 4: Alembic Migration Structure for New Tables

```python
# backend/alembic/versions/014_taxi_config.py
revision = "014_taxi_config"
down_revision = "013_draft_order_rules"

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS league_taxi_configs (
            id                  INTEGER PRIMARY KEY,
            league_id           VARCHAR NOT NULL UNIQUE,
            taxi_slots          INTEGER NOT NULL,
            taxi_years_eligible INTEGER NOT NULL,
            years_pro_cutoff    INTEGER NOT NULL,
            created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

# ALSO add to startup_tasks.py _SCHEMA_COMPAT_TABLES dict:
# "league_taxi_configs": "CREATE TABLE IF NOT EXISTS league_taxi_configs ..."

# ALSO add to tests/conftest.py SCHEMA_SQL list:
# "CREATE TABLE IF NOT EXISTS league_taxi_configs ..."
```

### Example 5: HygieneSuggestion Model

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict

HygieneActionType = Literal["consolidate", "cut", "stash", "taxi"]

class HygieneSuggestion(BaseModel):
    model_config = ConfigDict(frozen=False)

    action_type: HygieneActionType
    primary_player_ids: list[str]       # players to act on
    target_player_id: str | None = None  # for consolidate: the target player
    counterparty_roster_id: int | None = None  # for consolidate: the named manager
    counterparty_name: str | None = None
    reasoning: str                       # leads with slot-blocking reason for cut
    direction_fit_score: float           # 0-1; higher = more aligned with team direction
```

### Example 6: Frontend Component Skeleton (TitleWindowPanel)

```tsx
// frontend/src/components/lineup/TitleWindowPanel.tsx
// Follows the existing card pattern in league.$leagueId.tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import type { TitleWindowResult } from "@/api/types"

const WINDOW_BADGE_CLASS: Record<string, string> = {
  "Peak Window": "border-accent/20 bg-accent/10 text-accent-foreground",
  "Fading Window": "border-primary/25 bg-primary/12 text-primary",
  "Outside Window": "border-border/60 bg-transparent text-muted-foreground",
}
```

---

## Validation Architecture

### Backend Test Coverage

Each new engine requires a unit test module following the existing pattern in `backend/tests/`:

| Test File | What It Tests |
|-----------|---------------|
| `backend/tests/intelligence/test_lineup_engine.py` | Replacement level calculation per position, flex slot baseline, edge cases (single starter, no starters at position, SUPER_FLEX), starter score normalization |
| `backend/tests/intelligence/test_title_window.py` | All three label classifications, threshold boundary values, direction post-adjustment logic (D-08) |
| `backend/tests/intelligence/test_hygiene_engine.py` | Cut candidate scoring (slot-blocking primary), consolidation suggestion generation (calls PackageBuilder), stash/taxi distinction, max-5-per-type limit (D-13) |
| `backend/tests/integration/test_intelligence_router.py` | New endpoints: `GET /intelligence/lineup/{league_id}/{roster_id}`, `GET /intelligence/hygiene/{league_id}/{roster_id}` |
| `backend/tests/integration/test_taxi_config_router.py` | `GET /leagues/{league_id}/taxi-config` returns null when not configured; `PUT` saves and returns; subsequent `GET` returns saved config |

All tests use the in-memory `db` fixture from `conftest.py`. New tables (`league_taxi_configs`, `lineup_scores`, `hygiene_suggestions`) must be added to `conftest.py` SCHEMA_SQL before writing any test that touches them.

### Frontend Test Coverage

No explicit frontend test framework is in use for this project. Frontend validation is done via:
1. TypeScript type safety — all new API response types defined in `types.ts` must match backend Pydantic model fields exactly.
2. Empty/loading/error state rendering — each new component must render correctly in all three non-populated states (per UI-SPEC State Inventory).
3. Query invalidation correctness — after taxi config save, lineup and hygiene queries must show updated data.

### Schema Validation Checkpoints

Before any plan marks complete, verify:
- [ ] Migration file exists in `backend/alembic/versions/` with correct `down_revision`.
- [ ] `_SCHEMA_COMPAT_TABLES` in `startup_tasks.py` contains identical DDL.
- [ ] `SCHEMA_SQL` in `conftest.py` contains identical DDL.
- [ ] Running `pytest backend/tests/` with the new `db` fixture passes without "table not found" errors.

### Integration Validation Points

The success criteria from CONTEXT.md map to these verifiable checkpoints:

| Success Criterion | Validation Check |
|-------------------|-----------------|
| SC-1: Optimal starting lineup uses real league lineup constraints and replacement-level baselines | `LineupEngine.compute_all()` on a 12-team league produces per-position starter scores; spot-check lowest-starter team has scores near 0; highest-starter team has scores near 1 |
| SC-2: Title-window score visible on each team screen | `GET /intelligence/lineup/{league_id}/{roster_id}` returns `title_window_label` field; `TitleWindowPanel` renders the badge |
| SC-3: Direction labels can cite lineup-level reasons | Post-classification adjustment in `compute_league()` changes a "true_contender" to "fragile_contender" when title-window is "Outside Window" and win_now is high |
| SC-4: Roster-hygiene panel with stash, cut, taxi, consolidation | `GET /intelligence/hygiene/{league_id}/{roster_id}` returns suggestions in all four action types; `RosterHygienePanel` renders each section |
| SC-5: Taxi eligibility, IR occupancy, manual exceptions modeled per league | `GET /leagues/{league_id}/taxi-config` returns saved config; taxi-eligible players surfaced in hygiene suggestions; IR count shown in `TaxiIRSlotSummary` |

---

## Migration Numbering

Confirmed current state (HIGH confidence — from `backend/alembic/versions/`):
- Last used: `013_draft_order_rules` (down_revision = `012_retrospective_runs`)
- Next available: `014`

Phase 11 requires:
- `014_taxi_config` — `league_taxi_configs` table
- `015_lineup_scores` — `lineup_scores` table (per-roster lineup calculator output cache)
- `016_hygiene_suggestions` — `hygiene_suggestions` table (per-roster hygiene output cache)

Alternatively, tables 015 and 016 can be combined into a single migration `015_phase11_output_tables` to reduce migration count, following the pattern of `004_phase2_output_tables.py`.

---

*Phase 11 research complete: 2026-03-24*
