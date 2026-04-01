# Phase 21 Research: Player Value Trends & Market Inefficiency Trade Suggestions

**Researched:** 2026-03-31
**Confidence:** HIGH for all architectural findings — sourced from codebase direct reads

---

## User Constraints

### Locked Decisions (from 21-CONTEXT.md)

**Trend signal scope:**
- D-01: Track all 12 raw component scores plus startup ADP year-over-year as the external market signal
- D-02: Temporal scope is season-over-season historical comparison — projection model, not rolling snapshot window
- D-03: Output is both continuous delta (stored internally) and labeled `"will rise" / "will maintain" / "will fall"` on all surfaces
- D-04: Players with no snapshot history are backfilled from fantasy and statistical data

**Opportunity feed:**
- D-05: Feed is cross-league, sorted by impact score (gap magnitude × projection confidence); ownership symbol per card
- D-06: Opportunity card fields: player name/position, trend label, ADP gap, suggested action, leagues owned in, similar players with similarity score and context, confidence indicator
- D-07: Rank changes only when calendar state will affect the market; no time-based decay
- D-08: One unified list — buy-side and sell-side together, distinguished by suggested action label

**Phase 17 integration:**
- D-09: Trend adds supporting context only to Phase 17 recommendation cards as `supporting_factors[]` entries
- D-10: Conflict case (Phase 17 says buy-low, trend says will fall, or vice versa) surfaces a detailed conflict explanation inline — no automatic override
- D-11: `"will fall"` trend on an elite player weakens (not removes) the Phase 17 REC-05 anti-overreaction prior, proportional to trend confidence
- D-12: Trend signals must be wired into all Phase 17 card-emitting modules (trade, lineup, hygiene, picks, rookie, waiver)

**Trigger logic:**
- D-13: Trigger is gap + trend combination; both need not point the same direction (veteran buy-low for contending team is canonical)
- D-14: Gap magnitude is the primary surfacing gate; confidence modulates the flag display, not visibility
- D-15: Rank changes only when evidence that next calendar state will affect market (combine, NFL Draft, trade deadline, rookie fever)
- D-16: No player exclusions from the feed; all players eligible regardless of injury status or ownership

### Claude's Discretion
- Specific gap threshold values for surfacing (gap magnitude cutoff)
- Component score combinations that map to trend labels (derived from historical positional analysis)
- Similarity score algorithm (position + archetype + trajectory proximity)
- How startup ADP year-over-year delta is normalized across positions
- Alembic migration numbering (must not conflict with migrations through 020)
- Whether trend data is stored per-player per-season in a new table or computed on demand

### Deferred
- User-configurable trend confidence thresholds
- Per-league opportunity feed filtering beyond the ownership symbol
- Trend-based pick valuation integration with Phase 6 pick engine
- Historical opportunity feed accuracy grading (Phase 9 retrospectives)

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3.12 | 3.12 | Backend runtime | Project-locked (STATE.md) |
| FastAPI | current | API router for `/opportunities` endpoint | Project-locked |
| DuckDB 1.5.0 | 1.5.0 | All DB reads and writes | Project-locked; 10-17x faster than SQLite for analytical queries |
| Pydantic v2 | current | Domain models (`TrendResult`, `OpportunityCard`) | Established pattern across all engines |
| React 19 / Vite / TanStack Query | current | Frontend route and data fetching | Project-locked |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | ^0.511.0 | Icons (TrendingUp, TrendingDown, Minus, ChevronDown, CalendarClock, CircleDot) | Already installed; use for opportunity card icons |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stored `player_trends` table | Compute on demand from snapshots | On-demand is simpler but re-computes every request; stored table is correct for cross-league feed (single query, not per-league loop) |
| Season-over-season snapshot comparison | Rolling 4-week window | Season-over-season is D-02 — locked decision |

**Installation:** No new packages required. All dependencies already installed.

---

## Architecture Patterns

### Recommended Package Structure

```
backend/src/fantasy/trends/
├── __init__.py
├── constants.py          # TREND_LABELS, GAP_THRESHOLDS, SIMILARITY_WEIGHTS, CALENDAR_ESCALATION_STATES
├── models.py             # TrendResult, OpportunityFeedItem, SimilarPlayer, TrendSupportingFactor
├── trend_engine.py       # Season-over-season component delta → trend label + confidence
├── opportunity_engine.py # Cross-league opportunity feed construction + ranking
├── trend_repo.py         # Read/write player_trends table; read player_adp_baseline
└── similarity.py         # Similar player matching (position + archetype + component proximity)
```

```
backend/src/fantasy/routers/
└── opportunities.py      # GET /opportunities → OpportunityFeedResponse
```

```
frontend/src/
├── routes/opportunities.tsx
└── components/opportunities/
    ├── OpportunityCard.tsx
    ├── OpportunityCardList.tsx
    ├── TrendBadge.tsx
    ├── SuggestedActionBadge.tsx
    ├── OwnershipSymbol.tsx
    ├── SimilarPlayersSection.tsx
    ├── ConflictExplanationPanel.tsx
    ├── CalendarEscalationLabel.tsx
    └── ConfidenceIndicator.tsx
```

### Pattern 1: TrendEngine — Season-Over-Season Component Delta

**What:** Reads historical component scores for a player across two reference seasons, computes per-component deltas, aggregates into a trend direction and confidence.

**When to use:** Called during opportunity feed construction and when enriching Phase 17 recommendation cards.

**Key implementation decisions:**
- `player_trends` table stores one row per `(player_id, season)` with all 12 component scores plus `startup_adp`. This is the right choice: enables a JOIN query across seasons rather than an expensive snapshot payload parse loop.
- Component scores are read from `player_values` for the current season. For prior seasons, either (a) a historical `player_values` archive table or (b) the existing `league_snapshots` payload JSON. The snapshot payload at `state.rosters[*].player_values` contains `lens_market`, `lens_direction`, `comp_short_term`, `comp_age_curve` but NOT all 12 components — only the subset saved to `_build_league_state()`. This is a **critical gap**: the snapshot does not preserve all 12 component scores. Resolution: the `player_trends` table must be populated forward from each `ValuationEngine.compute_player()` call (same session that writes `player_values`), not reconstructed retroactively from snapshots.
- Backfill for players with no snapshot history (D-04): derive proxy component scores from `player_stats_weekly`, `player_adp_baseline`, and `players` (age, position) using the same formulas in `ValuationEngine`. This produces point-in-time component estimates without requiring actual snapshot history.

**Trend label bucketing (Claude's discretion):**
- Weighted aggregate delta across components: weight by component importance per position (e.g., `comp_age_curve` matters more for aging RBs; `comp_role_stability` matters more for young WRs)
- Delta thresholds: `will_rise` if weighted delta > +0.07; `will_fall` if < -0.07; `will_maintain` otherwise (0-bounded at position-specific calibration)
- Confidence = function of: number of seasons with data (more = higher), data completeness (all 12 present vs. backfilled proxies), and spread agreement across components (high agreement across components = HIGH confidence)

**Example model:**
```python
# Source: codebase pattern from intelligence/models.py + lineup/constants.py
from typing import Literal

TrendLabel = Literal["will_rise", "will_maintain", "will_fall"]
TrendConfidence = Literal["HIGH", "MEDIUM", "LOW"]

class TrendResult(BaseModel):
    player_id: str
    trend_label: TrendLabel
    confidence: TrendConfidence
    delta_magnitude: float          # signed float, raw aggregate delta
    component_deltas: dict[str, float]  # per-component deltas
    adp_delta: float | None         # startup ADP year-over-year change
    seasons_compared: int           # how many seasons of data
    backfilled: bool                # True if prior season used proxy scores
```

### Pattern 2: OpportunityEngine — Cross-League Feed Construction

**What:** Queries all players across all connected leagues, computes gap (model value vs. startup ADP), ranks by `gap_magnitude × projection_confidence`, attaches trend result, ownership info, similar players, and calendar escalation flag.

**When to use:** Called by the `/opportunities` GET endpoint.

**Key decisions:**
- `impact_score = gap_magnitude × confidence_multiplier` where `confidence_multiplier` is HIGH=1.0, MEDIUM=0.7, LOW=0.4
- Suggested action logic: `"sell"` if trend is `will_fall` AND gap is positive (overvalued by market); `"buy"` if trend is `will_rise` AND gap is negative (undervalued); `"hold"` otherwise — BUT direction-fit context overrides this in the veteran case (D-13): a veteran with `will_fall` who fits a contending team's 1-2 year window surfaces as `"buy"` with the context labeled clearly
- Calendar escalation: read `CalendarService.active_state()` and check against `CALENDAR_ESCALATION_STATES` (combine window, post_nfl_draft, trade_deadline, rookie_fever); if active, mark `calendar_escalated=True` with escalation label text

**Example model:**
```python
class SimilarPlayer(BaseModel):
    player_id: str
    player_name: str
    similarity_score: float       # 0–1
    archetype_label: str | None
    context: str                  # why comparable (e.g., "age 27 WR, similar role stability + ceiling profile")

class OpportunityFeedItem(BaseModel):
    player_id: str
    player_name: str
    position: str
    trend_label: TrendLabel
    trend_confidence: TrendConfidence
    adp_gap: float                # positive = player ranked higher than model value (overvalued by market)
    suggested_action: Literal["buy", "sell", "hold"]
    impact_score: float
    why_summary: str
    owned_in_leagues: list[str]   # league_id list; empty = not owned (buy target)
    similar_players: list[SimilarPlayer]
    conflict_explanation: str | None  # populated when Phase 17 gap classification disagrees
    calendar_escalated: bool
    calendar_escalation_label: str | None
```

### Pattern 3: Phase 17 Integration — `supporting_factors[]` Wiring

**What:** `TrendEngine` output is wrapped into `SupportingFactor` shape and injected into every Phase 17 card-emitting engine's output.

**When to use:** All card-emitting engines: TradeEngine, LineupEngine, HygieneEngine, PickEngine, RookieEngine, WaiverEngine.

**Entry shape (matching Phase 17 REC-02 contract):**
```python
# Phase 17 SupportingFactor shape — Phase 21 emits trend entries in this exact structure
{
    "factor_name": "Value Trend",
    "direction": "positive",   # positive=will_rise, negative=will_fall, neutral=will_maintain
    "magnitude": 0.74,         # trend confidence × delta_magnitude (normalized 0–1)
    "explanation": "Component scores project a rise next season — age curve is strong (27 WR), role stability trending up."
}
```

**Anti-overreaction weakening (D-11):**
- Hook: `ValuationEngine.compute_player()` accepts an optional `trend_result: TrendResult | None = None` parameter
- When `trend_result.trend_label == "will_fall"` AND player is elite (composite insulation+ceiling+floor above elite threshold), reduce the stabilization prior's dampening factor proportionally to `trend_result.confidence`: HIGH confidence = 70% reduction, MEDIUM = 40% reduction, LOW = 15% reduction
- This happens inside `_direction_lens()` or as a post-pass before returning `PlayerValue`
- Silent: no annotation on the output (per Phase 17 D-09)

### Pattern 4: New Table — `player_trends`

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS player_trends (
    id                      INTEGER PRIMARY KEY,
    player_id               VARCHAR NOT NULL,
    season                  INTEGER NOT NULL,
    trend_label             VARCHAR,
    confidence              VARCHAR,
    delta_magnitude         FLOAT,
    adp_delta               FLOAT,
    comp_current_production FLOAT,
    comp_short_term         FLOAT,
    comp_role_stability     FLOAT,
    comp_age_curve          FLOAT,
    comp_insulation         FLOAT,
    comp_market_liquidity   FLOAT,
    comp_positional_scarcity FLOAT,
    comp_fragility          FLOAT,
    comp_ceiling            FLOAT,
    comp_floor              FLOAT,
    comp_rerollability      FLOAT,
    comp_contract           FLOAT,
    startup_adp             FLOAT,
    backfilled              BOOLEAN NOT NULL DEFAULT FALSE,
    computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_id, season)
)
```

**Triple-write requirement:** This table must appear in all three schema locations:
1. `backend/alembic/versions/021_player_trends.py` — Alembic migration (next after 020)
2. `backend/src/fantasy/startup_tasks.py` — `_SCHEMA_COMPAT_TABLES["player_trends"]` entry
3. `backend/tests/conftest.py` — `SCHEMA_SQL` list entry

### Pattern 5: Similarity Score — Component + Archetype Proximity

**What:** For each opportunity card player, find the N most similar players in `player_trends` history.

**Algorithm (Claude's discretion resolution):**
- Feature vector: position (exact match required), `comp_age_curve`, `comp_ceiling`, `comp_floor`, `comp_role_stability`, `comp_short_term`, startup ADP tier (binned by round: 1.01–1.06, 1.07–1.12, 2.x, 3.x+)
- Distance: normalized Euclidean across the 5 numeric features, position-filtered
- Similarity score: `1 - (distance / max_distance_in_position_cohort)`, clamped 0–1
- Context string: template-generated from which features are close, e.g., "age 28 RB, similar role stability and floor trajectory"
- ADP tier binning avoids comparing a 1.01 prospect to an undrafted waiver player in the "similar players" section
- No ML library required — pure DuckDB arithmetic query or Python dict math on the trend table

### Pattern 6: Conflict Detection — Phase 17 Gap vs. Phase 21 Trend

**What:** Compare Phase 17 gap classification for a player against Phase 21 trend label. Conflict = directional disagreement.

**Conflict cases:**
- Phase 17 says `buy_low` (player undervalued by market) but trend says `will_fall` → user should understand the player is cheap NOW but won't hold value
- Phase 17 says `sell_high` (player overvalued) but trend says `will_rise` → selling a player who may genuinely be ascending
- Phase 17 says `hold_despite_weak_market` but trend says `will_fall` → the hold case weakens materially

**Non-conflict cases:**
- Phase 17 `buy_low` + trend `will_rise` → compatible signals; no conflict panel; single supporting factor
- Phase 17 `sell_high` + trend `will_fall` → compatible; strong sell signal

**Conflict explanation template:**
> "Phase 17 classifies this as {gap_classification} while the trend signal shows {trend_label}. {explanation}."

### Anti-Patterns to Avoid

- **Do not compute opportunity feed per-league in a loop and then merge:** the feed is cross-league by design (D-05); query all leagues at once with ownership grouped by player_id
- **Do not suppress LOW confidence cards from the feed:** gap magnitude is the gate (D-14); confidence is a display flag only
- **Do not add time-based rank decay:** D-07 and D-15 are explicit that rank changes only with calendar-state evidence
- **Do not store `RecommendationCard` instances with Phase 21 trend factors embedded:** Phase 17 cards are computed on demand; the trend `supporting_factors[]` entries are injected at card emission time, not stored separately
- **Do not parse the snapshot `payload_json` blob to reconstruct component scores:** the snapshot only persists a subset of component fields (confirmed by reading `snapshot_service.py` `_build_league_state()` — it stores `lens_market`, `lens_direction`, `comp_short_term`, `comp_age_curve` only); use `player_trends` as the durable per-season component store instead

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Component score distance calculation | Custom scoring distance formula from scratch | Pure arithmetic over `player_trends` table (5 normalized floats, Euclidean) | The dataset is small enough that DuckDB arithmetic suffices; no ML library needed |
| ADP year-over-year normalization | Complex position-adjusted ADP formula | Normalize per-position cohort: `(adp_current - avg_position_adp) / stdev_position_adp` — computable via DuckDB window functions | ADP is already position-stratified in `player_adp_baseline`; simple z-score is sufficient |
| Calendar state resolution | Custom date range logic | `CalendarService.active_state()` already exists and is correct | Re-implementing date windows would diverge from existing state machine |
| Gap classification | New classification system | Phase 17 gap classification labels (buy_low, sell_high, hold_despite_weak_market, etc.) are defined in MKT-03; reuse the enum | Adding Phase 21-specific classification creates two competing systems |
| Elite player detection for anti-overreaction | New "elite" flag column | Use the same composite score logic Phase 17 established for REC-05: combination of `comp_insulation`, `comp_ceiling`, `comp_floor` above threshold | One definition of "elite" must be shared between Phase 17 and Phase 21 or weakening logic diverges |

---

## Common Pitfalls

### Pitfall 1: Snapshot-as-Component-History

**Trap:** Reading `league_snapshots.payload_json` to reconstruct historical component scores for trend computation.

**Why it fails:** `SnapshotService._build_league_state()` only stores `lens_market`, `lens_direction`, `comp_short_term`, `comp_age_curve` per player — not all 12 components. Any attempt to build season-over-season deltas from snapshot JSON will silently produce partial data.

**Prevention:** The `player_trends` table is the durable component history store. Populate it each time `ValuationEngine.compute_player()` runs (write-through from the valuation pipeline). The snapshot remains a league-state archive; `player_trends` is the player-state archive.

### Pitfall 2: Migration Numbering Conflict

**Trap:** Using migration number 021 without verifying the head.

**Current head:** Migration 020 (`020_expand_prospect_feature_columns.py`) is the highest numbered file in `/backend/alembic/versions/`. The Phase 21 migration must be numbered `021_player_trends.py`.

**Prevention:** Verify with `ls backend/alembic/versions/ | sort | tail -5` before writing the migration file.

### Pitfall 3: Triple-Write Omission

**Trap:** Adding `player_trends` to the Alembic migration but forgetting `startup_tasks.py` and/or `conftest.py`.

**Why it matters:** New users running the app without `alembic upgrade head` get a missing table error. Tests fail silently if `conftest.py` doesn't include the table in `SCHEMA_SQL`. This is documented as a known gap in STATE.md.

**Prevention:** Any new table = write it in all three places in the same plan/task.

### Pitfall 4: Conflict Detection Logic Applied Too Broadly

**Trap:** Marking every trend/gap directional pairing that isn't perfectly aligned as a "conflict."

**Why it matters:** Phase 17 `hold_despite_weak_market` + trend `will_fall` IS a conflict. But `hold_despite_weak_market` + trend `will_maintain` is NOT a conflict — they are compatible signals. Over-flagging conflicts degrades signal quality and overwhelms the user.

**Prevention:** The conflict detection matrix must be explicitly coded, not inferred from a simple "direction equality" check. Write it as a lookup: `(gap_label, trend_label) -> is_conflict: bool`.

### Pitfall 5: Opportunity Feed Includes Duplicate Players Across Leagues

**Trap:** Building the feed per-league and concatenating lists, resulting in the same player appearing multiple times (once per league they're owned in).

**Why it matters:** D-05 says one card per player, with an ownership symbol indicating all leagues. Duplicates break the feed's utility.

**Prevention:** Group by `player_id` first, aggregate `owned_in_leagues` as a list, then build one card per player.

### Pitfall 6: Anti-Overreaction Weakening Applied to Non-Elite Players

**Trap:** Applying the D-11 prior weakening to any player with `trend_label == "will_fall"` rather than only to elite players.

**Why it matters:** The Phase 17 anti-overreaction prior is only relevant for elite players (high `comp_insulation + comp_ceiling + comp_floor` composite). For a low-value player with a "will fall" trend, the prior does nothing — there is no stabilization to weaken.

**Prevention:** Gate the weakening logic with the same elite-composite check used in Phase 17 REC-05. Call `_is_elite(player_value: PlayerValue) -> bool` before applying the weakening.

### Pitfall 7: `player_trends` Table Not Populated for Cross-League Players

**Trap:** Only writing `player_trends` rows for players on the active user's roster in the currently evaluated league, missing players on other managers' rosters who should appear in the cross-league opportunity feed.

**Why it matters:** D-16 says all players are eligible for the feed. If the trend engine only runs for owned players, the buy-target side of the feed is empty.

**Prevention:** `TrendEngine` must run against all players in `players` table (or at minimum all players appearing on any roster in any connected league), not just the user's rostered players.

---

## Code Examples

### Example 1: TrendEngine Core Loop (season-over-season delta)

```python
# Source: derived from valuation_engine.py compute_player() pattern
class TrendEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def compute_trend(self, player_id: str) -> TrendResult:
        rows = self._conn.execute(
            """
            SELECT season, comp_current_production, comp_short_term, comp_role_stability,
                   comp_age_curve, comp_insulation, comp_market_liquidity,
                   comp_positional_scarcity, comp_fragility, comp_ceiling,
                   comp_floor, comp_rerollability, comp_contract, startup_adp, backfilled
            FROM player_trends
            WHERE player_id = ?
            ORDER BY season DESC
            LIMIT 2
            """,
            [player_id],
        ).fetchall()
        # ... compute deltas, bucket to trend label, assign confidence
```

### Example 2: Triple-Write for `player_trends` — Alembic Migration

```python
# backend/alembic/versions/021_player_trends.py
revision = "021_player_trends"
down_revision = "020_expand_prospect_feature_columns"

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS player_trends (
            id                      INTEGER PRIMARY KEY,
            player_id               VARCHAR NOT NULL,
            season                  INTEGER NOT NULL,
            -- ... (all 12 component columns + startup_adp + trend_label + confidence + backfilled)
            UNIQUE (player_id, season)
        )
    """)
```

### Example 3: Conflict Detection Matrix

```python
# Source: conflict logic per CONTEXT.md D-10
CONFLICT_MATRIX: dict[tuple[str, str], bool] = {
    ("buy_low", "will_fall"): True,
    ("buy_low", "will_rise"): False,
    ("buy_low", "will_maintain"): False,
    ("sell_high", "will_rise"): True,
    ("sell_high", "will_fall"): False,
    ("sell_high", "will_maintain"): False,
    ("hold_despite_weak_market", "will_fall"): True,
    ("hold_despite_weak_market", "will_rise"): False,
    ("hold_despite_weak_market", "will_maintain"): False,
    ("market_right_model_cautious", "will_rise"): True,
    ("market_right_model_cautious", "will_fall"): False,
    ("ignore_false_discount", "will_rise"): True,
    ("ignore_false_discount", "will_fall"): False,
    ("league_specific_opportunity", "will_fall"): True,
    ("league_specific_opportunity", "will_rise"): False,
}

def is_conflict(gap_label: str, trend_label: str) -> bool:
    return CONFLICT_MATRIX.get((gap_label, trend_label), False)
```

### Example 4: Supporting Factor Injection (Phase 17 wiring)

```python
# Shape must match Phase 17 REC-02 contract exactly
def trend_to_supporting_factor(trend: TrendResult) -> dict:
    direction_map = {
        "will_rise": "positive",
        "will_fall": "negative",
        "will_maintain": "neutral",
    }
    return {
        "factor_name": "Value Trend",
        "direction": direction_map[trend.trend_label],
        "magnitude": round(abs(trend.delta_magnitude) * _confidence_multiplier(trend.confidence), 2),
        "explanation": _build_trend_explanation(trend),
    }
```

### Example 5: Opportunity Feed Router (established router pattern)

```python
# backend/src/fantasy/routers/opportunities.py
# Follows pattern from dashboard.py and intelligence.py
router = APIRouter(prefix="/opportunities", tags=["opportunities"])

@router.get("", response_model=OpportunityFeedResponse)
def get_opportunity_feed(conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn)) -> OpportunityFeedResponse:
    ...
```

### Example 6: Frontend API Type (established types.ts pattern)

```typescript
// frontend/src/api/types.ts — extend this file
export type TrendLabel = "will_rise" | "will_maintain" | "will_fall"
export type SuggestedAction = "buy" | "sell" | "hold"
export type TrendConfidence = "HIGH" | "MEDIUM" | "LOW"

export interface SimilarPlayer {
  player_id: string
  player_name: string
  similarity_score: number
  archetype_label: string | null
  context: string
}

export interface OpportunityFeedItem {
  player_id: string
  player_name: string
  position: string
  trend_label: TrendLabel
  trend_confidence: TrendConfidence
  adp_gap: number
  suggested_action: SuggestedAction
  impact_score: number
  why_summary: string
  owned_in_leagues: string[]
  similar_players: SimilarPlayer[]
  conflict_explanation: string | null
  calendar_escalated: boolean
  calendar_escalation_label: string | null
}

export interface OpportunityFeedResponse {
  items: OpportunityFeedItem[]
  total: number
  computed_at: string
}
```

---

## Validation Architecture

The planner MUST create a `21-VALIDATION.md` referencing these acceptance tests. Each plan should wire the relevant test block into its verification step.

### Block A: TrendEngine — trend label and confidence correctness

**Test file:** `backend/tests/trends/test_trend_engine.py`

| Test | What it verifies |
|------|-----------------|
| `test_trend_engine_will_rise` | Player with improving component scores across two seasons produces `trend_label == "will_rise"` |
| `test_trend_engine_will_fall` | Player with deteriorating scores (especially `comp_age_curve` decline) produces `trend_label == "will_fall"` |
| `test_trend_engine_will_maintain` | Player with flat component scores produces `trend_label == "will_maintain"` |
| `test_trend_confidence_high` | Two full seasons of non-backfilled data with agreement across components → `confidence == "HIGH"` |
| `test_trend_confidence_low` | Backfilled prior season + single component divergence → `confidence == "LOW"` |
| `test_trend_backfill_proxy` | Player with no snapshot history produces a valid `TrendResult` with `backfilled == True` |
| `test_trend_adp_delta` | `adp_delta` is positive when startup ADP rose (player ranked higher = lower ADP number = risen in market) |

### Block B: OpportunityEngine — feed construction and ranking

**Test file:** `backend/tests/trends/test_opportunity_engine.py`

| Test | What it verifies |
|------|-----------------|
| `test_feed_sorted_by_impact_score` | Items sorted descending by `impact_score`; item with larger gap × higher confidence ranks above item with smaller gap × lower confidence |
| `test_feed_deduplicates_players` | A player owned in two leagues appears once with both league IDs in `owned_in_leagues` |
| `test_feed_buy_target_no_symbol` | Player not owned in any league has `owned_in_leagues == []` |
| `test_suggested_action_sell` | `trend_label == "will_fall"` and positive `adp_gap` (overvalued) → `suggested_action == "sell"` |
| `test_suggested_action_buy` | `trend_label == "will_rise"` and negative `adp_gap` (undervalued) → `suggested_action == "buy"` |
| `test_veteran_buy_low_contending_team` | Player with `will_fall` trend on contending team surfaces as `"buy"` when direction-fit context applies |
| `test_low_confidence_not_suppressed` | LOW confidence player with large gap appears in feed |
| `test_calendar_escalation_flag` | Calendar state == `"post_combine"` → eligible player has `calendar_escalated == True` |
| `test_no_calendar_escalation` | Calendar state == `"early_season"` (non-escalation) → `calendar_escalated == False` |

### Block C: Conflict Detection

**Test file:** `backend/tests/trends/test_conflict_detection.py`

| Test | What it verifies |
|------|-----------------|
| `test_conflict_buy_low_will_fall` | `("buy_low", "will_fall")` → `is_conflict == True` |
| `test_no_conflict_buy_low_will_rise` | `("buy_low", "will_rise")` → `is_conflict == False` |
| `test_conflict_sell_high_will_rise` | `("sell_high", "will_rise")` → `is_conflict == True` |
| `test_conflict_hold_despite_weak_market_will_fall` | `("hold_despite_weak_market", "will_fall")` → `is_conflict == True` |
| `test_conflict_explanation_populated` | When conflict detected, `conflict_explanation` on `OpportunityFeedItem` is non-null and non-empty |

### Block D: Phase 17 Supporting Factor Wiring

**Test file:** `backend/tests/trends/test_trend_supporting_factor.py`

| Test | What it verifies |
|------|-----------------|
| `test_trend_factor_shape` | `trend_to_supporting_factor()` returns dict with exactly `factor_name`, `direction`, `magnitude`, `explanation` keys |
| `test_trend_factor_direction_will_rise` | `trend_label == "will_rise"` → `direction == "positive"` |
| `test_trend_factor_direction_will_fall` | `trend_label == "will_fall"` → `direction == "negative"` |
| `test_trend_factor_direction_will_maintain` | `trend_label == "will_maintain"` → `direction == "neutral"` |
| `test_magnitude_positive` | `magnitude` is always >= 0 |

### Block E: Anti-Overreaction Weakening (D-11)

**Test file:** `backend/tests/trends/test_anti_overreaction_weakening.py`

| Test | What it verifies |
|------|-----------------|
| `test_elite_player_will_fall_high_confidence` | Elite player with `will_fall` + HIGH confidence → stabilization prior reduced by ~70% vs. baseline |
| `test_elite_player_will_fall_low_confidence` | Elite player with `will_fall` + LOW confidence → stabilization prior reduced by ~15% vs. baseline |
| `test_non_elite_player_no_weakening` | Non-elite player with `will_fall` → no stabilization reduction applied |
| `test_will_rise_no_weakening` | `will_rise` trend on any player → no weakening logic triggered (D-11 is will_fall only) |

### Block F: Schema Triple-Write

**Test file:** Verified in existing `backend/tests/conftest.py` pattern — new table present in `SCHEMA_SQL`.

| Test | What it verifies |
|------|-----------------|
| `player_trends` in `SCHEMA_SQL` | Table created in test DB without error |
| `player_trends` in `_SCHEMA_COMPAT_TABLES` | `startup_tasks.ensure_runtime_schema()` creates table if absent |
| Migration `021_player_trends` runs cleanly | `alembic upgrade head` produces no error with the new migration |

### Block G: Frontend — Opportunity Feed Route

**Test file:** Visual verification (no automated tests for frontend in this project); planner should include a manual verification checklist.

| Check | What it verifies |
|-------|-----------------|
| `/opportunities` route renders `OpportunityFeedPage` | Route registered in `__root.tsx` or equivalent |
| `TrendBadge` applies correct color per label | `will_rise` → primary treatment; `will_fall` → destructive; `will_maintain` → accent |
| `SuggestedActionBadge` applies correct color | Same color scheme as TrendBadge |
| `ConflictExplanationPanel` visible (not collapsed) by default | Amber container renders when `conflict_explanation` is non-null |
| `SimilarPlayersSection` collapsed by default | Collapsed on initial render; expands on chevron click |
| Dashboard link to `/opportunities` present | "View Opportunities" link in Cross-League Exposure card footer |
| Dashboard stat tile shows opportunities count | Stat tile matches `OpportunityFeedResponse.total` |

---

## Integration Map

This summarizes every integration point Phase 21 touches in existing code. The planner must address each one.

| Existing File | What Phase 21 Does To It |
|---------------|--------------------------|
| `backend/src/fantasy/intelligence/valuation_engine.py` | Add optional `trend_result` param to `compute_player()`; apply D-11 prior weakening in `_direction_lens()` when trend is `will_fall` and player is elite |
| `backend/src/fantasy/intelligence/models.py` | No changes — `PlayerValue` model unchanged |
| `backend/src/fantasy/context/calendar_service.py` | Read-only; `CalendarService.active_state()` called by `OpportunityEngine` |
| `backend/src/fantasy/snapshots/snapshot_service.py` | No changes — snapshots are NOT used as component history source (see Pitfall 1) |
| `backend/src/fantasy/startup_tasks.py` | Add `player_trends` to `_SCHEMA_COMPAT_TABLES` |
| `backend/tests/conftest.py` | Add `player_trends` DDL to `SCHEMA_SQL` list |
| `backend/alembic/versions/` | Add `021_player_trends.py` |
| `backend/src/fantasy/routers/` | Add `opportunities.py`; register in main app |
| All Phase 17 card-emitting engines (when Phase 17 executes) | Add `TrendEngine` injection and `trend_to_supporting_factor()` call; this is a Phase 21 TODO seeded into Phase 17's plan |
| `frontend/src/api/types.ts` | Add `TrendLabel`, `SuggestedAction`, `TrendConfidence`, `SimilarPlayer`, `OpportunityFeedItem`, `OpportunityFeedResponse` types |
| `frontend/src/routes/index.tsx` | Add "Opportunities" stat tile + "View Opportunities" link in Cross-League Exposure card footer |
| `frontend/src/routes/` | Add `opportunities.tsx` route |

---

## Open Questions for Planner

1. **Phase 17 execution order:** Phase 17 (recommendation contract) is currently unplanned (0/0 plans, ROADMAP.md). The Phase 21 CONTEXT.md D-12 says trend signals must be wired into all Phase 17 card-emitting modules. The correct sequencing is: Phase 21 builds `TrendEngine` + the `/opportunities` feed standalone; Phase 17 wires the trend `supporting_factors[]` into its cards. The planner should seed a Phase 17 integration TODO into Phase 21 plans rather than trying to execute Phase 17 work here.

2. **`player_trends` population timing:** The planner must decide when `player_trends` is written: (a) as a write-through whenever `ValuationEngine.compute_player()` runs (most complete), or (b) as a batch job triggered after each ingest cycle. Option (a) is recommended — it requires the least new infrastructure.

3. **Backfill data completeness:** D-04 says backfill is possible from fantasy and statistical data. The `player_stats_weekly` and `player_adp_baseline` tables exist. The planner should include a one-time backfill task to populate historical `player_trends` rows for prior seasons using proxy scores computed from the existing `ValuationEngine` formula on historical stat data.
