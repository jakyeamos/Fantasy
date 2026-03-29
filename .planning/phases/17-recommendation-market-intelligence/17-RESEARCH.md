# Phase 17 Research: Recommendation Contract & Market Intelligence

**Researched:** 2026-03-28
**Phase:** 17 — recommendation-market-intelligence
**Requirements in scope:** REC-01, REC-02, REC-03, REC-04, REC-05, REC-06, MKT-01, MKT-02, MKT-03, MKT-04, MKT-05

---

## User Constraints

### Locked Decisions (Planner MUST honor — from 17-CONTEXT.md)

**Recommendation card emission:**
- D-01: Cards emitted alongside existing output shapes as `recommendation_cards: list[RecommendationCard]`; existing fields not removed
- D-02: All major modules in scope this phase: trade, lineup/hygiene, direction/scorecard, picks, waiver, rookie, orphan intake; where a module lacks sufficient foundation, add a TODO in the relevant phase plan
- D-03: `cta_destination` is a route key or path string; backend emits intent, frontend owns CTA routing
- D-04: Partial shapes (e.g., `strategic_distinction` in `TradeEvaluation`) replaced by full `RecommendationCard` if card is more actionable; coexistence only acceptable during transient migration

**Priority ranking formula:**
- D-05: `priority = impact × confidence × execution × urgency` — uniform across all modules, same weights
- D-06: `supporting_factors[]` — each factor carries `factor_name`, `direction`, `magnitude`, `explanation`

**Anti-overreaction layer:**
- D-07: Layer applies to both `PlayerValue` component scores AND recommendation card output — gates at model level
- D-08: "Elite" defined by combination of `PlayerValue` scores (not a single field) — composite threshold is Claude's discretion
- D-09: Stabilization is silent — only final stabilized conclusion shown; no "insulation prior applied" annotation
- D-10: Bidirectional — dampens bearish overcorrection on elite players AND bullish overclaiming on low-insulation breakout candidates

**Player context flags:**
- D-11: Flags sourced from real data feed — not manual entry
- D-12: Flags are player-scoped (global across all leagues), not league-scoped
- D-13: A context flag always triggers a change on the recommendation card — no materiality gate
- D-14: Flags expire automatically — expiry logic is Claude's discretion (TTL, ingest-triggered, or calendar-state transition)

**Market value and model-vs-market gap:**
- D-15: External market data introduced this phase; league trade history (revealed preferences) is primary signal; external signal fills gaps where no league-specific trades exist
- D-16: `lens_market` becomes true market-calibrated value (external baseline + league revealed preference weighting)
- D-17: Manager-demand value implemented via either extending Phase 12 pick-premium signal or building new per-player demand model — Claude determines during research
- D-18: Gap classification cutoffs are Claude's discretion
- D-19: "Hold despite weak market" is a first-class conclusion surfaced with same prominence as buy/sell

### Claude's Discretion Areas
- Composite elite-tier threshold definition (D-08)
- Which external market data source to integrate (KTC vs. FantasyCalc vs. Sleeper ADP)
- Whether manager-demand value extends Phase 12 or builds new per-player demand model (D-17)
- Context flag expiry logic: TTL duration, ingest-triggered expiry, or calendar-state transition (D-14)
- Alembic migration numbering (must not conflict with 015–020 already in use)
- DB schema for context flags table, market value columns, and recommendation card storage
- Whether `RecommendationCard` is stored in DB or computed on demand

### Deferred Ideas (Out of scope — ignore)
- User-configurable anti-overreaction sensitivity
- Cross-league market gap comparison
- Surfacing which specific trades drove the league market value signal
- Manual context flag override / admin entry fallback

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0 (project dep) | `RecommendationCard` model definition, all new Pydantic models | Already the project model layer; Literal unions, field validators, model_copy() |
| duckdb | 1.5.0 (project dep) | Player context flags table, market value columns, recommendation card persistence if stored | All project data; DuckDB DDL only, no SQLite |
| httpx | >=0.27 (project dep) | FantasyCalc API calls (external market baseline) | Already the project HTTP client; async context manager pattern established |
| fastapi | >=0.115 (project dep) | Router response model additions (`recommendation_cards` field) | Project web framework |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | >=8.2 (project dep) | Retry wrapper around FantasyCalc API calls | Same pattern as `SleeperClient._get()` — use `retry_if_exception` for 429/5xx |
| polars | >=1.0 (project dep) | Batch processing trade history for market value computation | Existing pattern in nfl_data_loader; efficient for aggregate queries over `transactions` table |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FantasyCalc API | KeepTradeCut (KTC) | KTC has no public API — scraping only, fragile and against ToS. FantasyCalc has a documented REST endpoint that powers their own site. FantasyCalc preferred. |
| FantasyCalc API | Sleeper ADP (`player_adp_baseline` table) | Sleeper ADP is already ingested and provides a fallback baseline. However, it is redraft-oriented and lacks dynasty-specific signals. FantasyCalc provides dynasty values, trend data, and positional rank alongside value. |
| Computed-on-demand cards | Store in DB | Storage adds migration complexity but enables list/filter queries and audit trail. Computed-on-demand is simpler, consistent with how most engines work today (computed when requested, optionally cached). Recommended: compute-on-demand with optional caching row (same pattern as `waiver_recommendations` table). |

**Installation:** No new packages required. All dependencies already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/src/fantasy/
├── recommendation/           # new module — RecommendationCard model, engine, gap engine
│   ├── __init__.py
│   ├── models.py             # RecommendationCard, SupportingFactor, MarketGap, PlayerContextFlag
│   ├── card_engine.py        # RecommendationCardEngine — assembles cards per module output
│   ├── anti_overreaction.py  # AntiOverreactionLayer — applies stabilizing prior inside ValuationEngine
│   ├── gap_engine.py         # MarketGapEngine — computes model-vs-market gap, classifies gap type
│   └── card_repo.py          # optional: cache write/read for recommendation_cards_cache table
├── market/                   # new module — external market data ingestion
│   ├── __init__.py
│   ├── fantasycalc_client.py # HTTP client for FantasyCalc API (async, tenacity retry)
│   ├── market_service.py     # MarketService — fetch, normalize, merge with league trade history
│   └── models.py             # ExternalPlayerValue, LeagueMarketSignal
├── player_flags/             # new module — player context flags
│   ├── __init__.py
│   ├── models.py             # PlayerContextFlag, FlagType Literal
│   ├── flag_engine.py        # FlagEngine — derives flags from Sleeper player fields
│   └── flag_repo.py          # FlagRepo — upsert/expire/read from player_context_flags table
```

### Pattern 1: RecommendationCard Pydantic Model

**What:** Single shared output contract for all modules (REC-01).
**When to use:** Attached as `recommendation_cards: list[RecommendationCard] | None = None` on every major response model.
**Example (from project Literal union pattern — Phase 11 precedent):**

```python
# backend/src/fantasy/recommendation/models.py
from typing import Literal
from pydantic import BaseModel, ConfigDict

RecommendationTypeLabel = Literal[
    "trade", "start", "drop", "hold", "shop", "package",
    "taxi", "reroll", "bid", "stash", "direction"
]

GapClassification = Literal[
    "buy_low", "sell_high", "hold_despite_weak_market",
    "ignore_false_discount", "market_right_model_cautious", "league_specific_opportunity"
]

HorizonLabel = Literal["immediate", "this_week", "30_days", "offseason", "next_season"]

ConfidenceLabel = Literal["HIGH", "MEDIUM", "LOW"]

class SupportingFactor(BaseModel):
    model_config = ConfigDict(frozen=False)
    factor_name: str
    direction: Literal["positive", "negative", "neutral"]
    magnitude: Literal["high", "medium", "low"]
    explanation: str

class ModelVsMarketGap(BaseModel):
    model_config = ConfigDict(frozen=False)
    market_rank: int | None = None
    model_rank: int | None = None
    market_value: float | None = None
    model_value: float | None = None
    gap_magnitude: float | None = None
    gap_direction: Literal["model_above", "model_below", "aligned"] | None = None
    gap_classification: GapClassification | None = None
    explanation: str | None = None

class RecommendationCard(BaseModel):
    model_config = ConfigDict(frozen=False)
    recommendation_type: RecommendationTypeLabel
    priority_rank: int                            # computed: impact × confidence × execution × urgency
    headline: str
    action: str
    target_entity_type: Literal["player", "pick", "position", "manager"]
    target_entity_ids: list[str]
    why_summary: str
    supporting_factors: list[SupportingFactor]
    confidence_label: ConfidenceLabel
    confidence_score: float                       # 0.0–1.0
    downside_of_inaction: str
    what_would_change_this_call: str
    horizon: HorizonLabel
    league_specificity_notes: str | None = None
    manager_specificity_notes: str | None = None
    model_vs_market_gap: ModelVsMarketGap | None = None
    cta_label: str
    cta_destination: str                          # route key/path, e.g. "/league/{league_id}/trade"
```

Source: REC-01, REC-02 from REQUIREMENTS.md; Literal union pattern from Phase 11 (Phase 11 decision logged in STATE.md).

### Pattern 2: Attaching Cards to Existing Response Models

**What:** Add `recommendation_cards: list[RecommendationCard] | None = None` to existing models.
**When to use:** Every primary response model in scope gets this field.
**Retrofit targets:**

```python
# TradeEvaluation (trade/models.py) — also replaces strategic_distinction per D-04
class TradeEvaluation(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None  # replaces strategic_distinction

# LineupResult (lineup/models.py)
class LineupResult(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None

# HygieneResult (lineup/models.py)
class HygieneResult(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None

# WaiverRecommendationsResponse (waiver/models.py)
class WaiverRecommendationsResponse(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None

# RookieBoardResult (rookie/models.py)
class RookieBoardResult(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None

# DraftRoomResult (rookie/models.py)
class DraftRoomResult(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None

# ActionPlan (waiver/models.py — orphan intake / startup)
# ActionPlanItem already has priority_rank, confidence_label, headline, action pattern
# ActionPlan gains recommendation_cards for module-level summary cards
class ActionPlan(BaseModel):
    ...
    recommendation_cards: list[RecommendationCard] | None = None
```

Note: `ActionPlanItem` in `waiver/models.py` already carries `priority_rank`, `confidence_label`, `headline`, `action`, `target_entity_type`, `target_entity_ids` — these partially overlap with `RecommendationCard`. The planner should decide whether `ActionPlanItem` is replaced by `RecommendationCard` (D-04 applies) or coexists. The safer option: replace, since the card is strictly more complete.

### Pattern 3: Anti-Overreaction Layer in ValuationEngine

**What:** Applies stabilizing priors at component score level inside `compute_player()`, after raw scores are computed but before lenses are derived. Silent — no annotation (D-09).
**Integration point:** `ValuationEngine.compute_player()` in `backend/src/fantasy/intelligence/valuation_engine.py` — after line 102 (all 12 components computed), before lens computations.

**Elite composite definition (D-08 — Claude's discretion):**
A player qualifies as elite when ALL of the following hold:
- `comp_insulation >= 0.70`
- `comp_ceiling >= 0.65`
- `comp_floor >= 0.50`
- `comp_age_curve >= 0.50`

Rationale: Insulation alone can be moderate for an undervalued elite player. Requiring ceiling + floor + age_curve ensures the composite captures established high-quality assets regardless of a single anomalous component.

**Stabilization rules (D-07, D-10, bidirectional):**
1. Bearish dampening (elite protection): if player is elite AND `comp_current_production < 0.40`, apply a floor pull toward `max(comp_current_production, 0.40)` — prevents raw one-year dip from collapsing the score
2. Bullish dampening (breakout guard): if player is NOT elite (low insulation, ≤0.40) AND `comp_ceiling >= 0.80`, cap ceiling contribution to `min(comp_ceiling, 0.65)` — prevents one-year spike from false ceiling signal
3. Contextual override: if a context flag of type `injury_recovery` or `role_compression` is active on the player, the bearish dampening in rule 1 is bypassed — a real contextual explanation earns the score movement

```python
# backend/src/fantasy/recommendation/anti_overreaction.py
ELITE_INSULATION_THRESHOLD = 0.70
ELITE_CEILING_THRESHOLD = 0.65
ELITE_FLOOR_THRESHOLD = 0.50
ELITE_AGE_CURVE_THRESHOLD = 0.50
BEARISH_PRODUCTION_FLOOR = 0.40
BULLISH_CEILING_CAP = 0.65
LOW_INSULATION_THRESHOLD = 0.40
BREAKOUT_CEILING_THRESHOLD = 0.80

def is_elite(value: PlayerValue) -> bool:
    return (
        (value.comp_insulation or 0.0) >= ELITE_INSULATION_THRESHOLD
        and (value.comp_ceiling or 0.0) >= ELITE_CEILING_THRESHOLD
        and (value.comp_floor or 0.0) >= ELITE_FLOOR_THRESHOLD
        and (value.comp_age_curve or 0.0) >= ELITE_AGE_CURVE_THRESHOLD
    )

def apply_stabilization(value: PlayerValue, active_flag_types: list[str]) -> PlayerValue:
    # bearish dampening
    if is_elite(value) and "injury_recovery" not in active_flag_types and "role_compression" not in active_flag_types:
        if (value.comp_current_production or 0.0) < BEARISH_PRODUCTION_FLOOR:
            value.comp_current_production = BEARISH_PRODUCTION_FLOOR
    # bullish dampening
    if (value.comp_insulation or 0.0) <= LOW_INSULATION_THRESHOLD:
        if (value.comp_ceiling or 0.0) >= BREAKOUT_CEILING_THRESHOLD:
            value.comp_ceiling = BULLISH_CEILING_CAP
    return value
```

### Pattern 4: Player Context Flags

**Data source (D-11):** Sleeper `/players/nfl` endpoint — already called via `SleeperClient.fetch_players()`. Player objects contain `depth_chart_order`, `depth_chart_position`, `injury_status`, `status`, `team`, and `news_updated`.

**Flag derivation — mapping Sleeper fields to flag types:**

| Flag Type | Source Field | Derivation Logic |
|-----------|-------------|-----------------|
| `injury_recovery` | `injury_status` | Non-null and in ("IR", "Out", "Doubtful") |
| `depth_chart_competition` | `depth_chart_order` | Order >= 2 for a skill position (QB/RB/WR/TE) |
| `role_expansion` | `depth_chart_order` | Changed from >=2 to 1 since last ingest |
| `role_compression` | `depth_chart_order` | Changed from 1 to >=2 since last ingest |
| `team_change` | `team` | Team value differs from previously stored team |
| `age_cliff_proximity` | `age` (from `players` table) | Player age within 1 year of `POSITIONAL_CLIFF_AGE` |

Note: Coaching changes and QB changes are NOT directly available from Sleeper player fields (confirmed via docs review). The `team_change` flag is a proxy for system changes. `news_updated` timestamp indicates recent news exists but does not carry semantic type. The planner should model coaching/QB-change flags as derived from `team_change` for now, with a TODO noting that a supplemental data source (e.g., FantasyCalc trend signal or manual seed from a news API) would improve precision.

**Expiry logic (D-14 — Claude's discretion):**
- `injury_recovery`: expires when `injury_status` is null or "Active" on next player ingest
- `depth_chart_competition` / `role_expansion` / `role_compression`: expire on next player ingest (they are re-evaluated from current Sleeper data each time)
- `team_change`: expires after 30 days (TTL = 30 days from flag creation) — team changes are structurally significant for the full season but should not persist indefinitely
- `age_cliff_proximity`: no expiry — re-derived on each computation from player age
- All flags: if `news_updated` has advanced beyond the flag creation timestamp by more than 14 days without a reingest, mark stale but do not auto-delete

**DB schema for player_context_flags:**
```sql
CREATE TABLE IF NOT EXISTS player_context_flags (
    id              INTEGER PRIMARY KEY,
    player_id       VARCHAR NOT NULL,
    flag_type       VARCHAR NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP,
    source          VARCHAR NOT NULL DEFAULT 'sleeper_ingest',
    metadata_json   VARCHAR,
    UNIQUE (player_id, flag_type)
)
```

### Pattern 5: External Market Data (FantasyCalc API)

**Endpoint:** `GET https://api.fantasycalc.com/values/current`
**Key parameters:** `isDynasty=true`, `numQbs` (1 or 2), `numTeams` (league team count), `ppr` (1, 0.5, or 0)

**Response shape (verified via live API call):**
```json
{
  "player": {
    "id": 9833,
    "name": "Bijan Robinson",
    "mflId": "16161",
    "position": "RB",
    "maybeTeam": "ATL",
    "maybeAge": 24.2,
    "maybeYoe": 3
  },
  "value": 10969,
  "overallRank": 1,
  "positionRank": 1,
  "trend30Day": -83,
  "redraftDynastyValueDifference": -499,
  "redraftValue": 10470,
  "combinedValue": 21439
}
```

**Confidence: HIGH** — Verified via live API call to `api.fantasycalc.com`.

**Player ID join strategy:** FantasyCalc uses `mflId` (MFL player ID). Sleeper uses Sleeper player IDs. The `players` table contains Sleeper IDs. A name + position + team fuzzy match is required, or a stored `mfl_id` column on the `players` table. The planner should add an `mfl_id` column to `players` in the migration, populated during market data ingest.

**DB schema for market_values table:**
```sql
CREATE TABLE IF NOT EXISTS market_values (
    id                  INTEGER PRIMARY KEY,
    player_id           VARCHAR NOT NULL,          -- Sleeper player_id
    fetched_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fantasycalc_value   FLOAT,                     -- dynasty value (0–10000+ scale)
    fantasycalc_rank    INTEGER,                   -- overall rank
    fantasycalc_trend30 FLOAT,                     -- 30-day trend (positive = rising)
    adp_baseline        FLOAT,                     -- from player_adp_baseline (redraft signal)
    UNIQUE (player_id)
)
```

**Cache freshness:** FantasyCalc values update daily. Fetch once per day maximum (enforce via `fetched_at` comparison). The `FreshnessService` pattern in `context/freshness_service.py` is the model for staleness tracking.

### Pattern 6: League Market Signal (Revealed Preferences from Trade History)

**Source:** `transactions` table WHERE `type = 'trade'` — already used by `ProfilingEngine._load_trades()`.
**Extend Phase 12 approach vs. new per-player model (D-17):**

Extending Phase 12 is the correct approach. The Phase 12 `_compute_value_delta()` method in `ProfilingEngine` already computes relative trade value from ADP. The extension needed:
1. Aggregate all trades in a league where player X appears on the "received" side
2. Use the value of assets sent in exchange (ADP-normalized) as the revealed market price for X
3. Weight recent trades more heavily (exponential decay on `created_at`)
4. Cap influence at 5 most recent trades to avoid stale signals dominating

This is a per-player, per-league signal — correct scope per D-12 (flags are player-scoped/global, but market value is inherently league-scoped since it's revealed by that league's trades).

**`lens_market` final computation (D-16):**
```
lens_market = 0.60 * league_revealed_preference + 0.40 * fantasycalc_normalized
```
Where `fantasycalc_normalized = 1 - (fantasycalc_rank / total_players)` scaled to [0,1]. If no league trades exist for a player, `league_revealed_preference = 0.5` (neutral), so external signal dominates by default.

### Pattern 7: Model-vs-Market Gap Classification (MKT-02, MKT-03)

**Inputs:** `lens_market` (market value), `lens_production` (model's production view), gap = `lens_production - lens_market`.

**Gap classification thresholds (D-18 — Claude's discretion):**

| Gap Direction | Magnitude | Classification |
|---------------|-----------|----------------|
| Model above market (gap > 0) | > 0.20 | `buy_low` |
| Model above market | 0.10–0.20 | `league_specific_opportunity` |
| Model above market | < 0.10 | `market_right_model_cautious` |
| Aligned | -0.10 to 0.10 | depends on model confidence |
| Model below market (gap < 0) | -0.10 to -0.20 | `ignore_false_discount` (model skeptical) |
| Model below market | < -0.20 | `sell_high` |
| Aligned + anti-overreaction fired on this player | any | `hold_despite_weak_market` |

Note: `hold_despite_weak_market` requires the anti-overreaction layer to have fired a bearish dampening on the same player in the same computation cycle. It is derived, not just from gap magnitude.

### Pattern 8: Priority Rank Computation (REC-04, D-05)

```python
def compute_priority(
    impact: float,       # 0.0–1.0: title equity / EV effect
    confidence: float,   # 0.0–1.0: model trust
    execution: float,    # 0.0–1.0: realistic pullability
    urgency: float,      # 0.0–1.0: downside of waiting
) -> int:
    raw_score = impact * confidence * execution * urgency
    # Scale to 1–100 integer rank (lower = higher priority, consistent with existing priority_rank int on ActionPlanItem)
    return max(1, min(100, round((1.0 - raw_score) * 99) + 1))
```

Note: `ActionPlanItem` already carries `priority_rank: int` — this encoding (int, lower = more important) is already established in the project.

### Pattern 9: Engine Injection into IntelligenceService

**What:** New engines follow the same injection pattern as existing engines.
**When to use:** `RecommendationCardEngine`, `MarketGapEngine`, `FlagEngine` all injected in `IntelligenceService.__init__()`.

```python
# backend/src/fantasy/intelligence/intelligence_service.py (addition)
from fantasy.recommendation.card_engine import RecommendationCardEngine
from fantasy.recommendation.gap_engine import MarketGapEngine
from fantasy.player_flags.flag_engine import FlagEngine
from fantasy.market.market_service import MarketService

class IntelligenceService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        ...
        self._rec_card_engine = RecommendationCardEngine(conn)
        self._market_gap_engine = MarketGapEngine(conn)
        self._flag_engine = FlagEngine(conn)
        self._market_service = MarketService(conn)
```

### Anti-Patterns to Avoid

- **Module-specific priority weights:** D-05 mandates uniform formula across all modules. Do not create per-module impact or urgency scaling constants.
- **Exposing anti-overreaction internals:** D-09 mandates silent stabilization. No `insulation_prior_applied: bool` field, no "stabilized" annotation on card output.
- **Replacing `RecommendationContext`:** The existing `RecommendationContext` (calendar state, freshness tags) is NOT replaced — it coexists on `TradeEvaluation` and other models. `RecommendationCard` is a new parallel field, not a takeover of the context pattern.
- **Storing full card objects as primary persistence:** Cards are computation outputs. Recommendation card storage (if any) should be a lightweight cache row with JSON blob (like `waiver_recommendations` table), not a normalized relational schema.
- **Blocking all routers on FantasyCalc availability:** External market data fetch should fail gracefully — if FantasyCalc is unavailable, `lens_market` falls back to ADP-only computation and cards are still emitted without `model_vs_market_gap`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with backoff to FantasyCalc | Custom retry loop | `tenacity` (`@retry` decorator, already in deps) | Same pattern as `SleeperClient._get()` — handles 429, 5xx, network errors |
| Player name fuzzy match for ID join | Custom edit-distance string match | Store `mfl_id` on `players` table during market ingest; fall back to name+position+team match | Direct ID join is O(1) vs O(N) fuzzy match; handle the fallback only for missing mfl_id rows |
| Confidence label derivation from float | Custom threshold logic | Establish `HIGH >= 0.75, MEDIUM >= 0.50, LOW < 0.50` as a shared constant in `recommendation/constants.py` | Consistent with existing `DimensionScore.confidence: Literal["HIGH","MEDIUM","LOW"]` pattern |
| Gap classification | Switch statement repeated per module | `MarketGapEngine.classify(gap_value, anti_overreaction_fired)` — single centralized classifier | Gap thresholds are Claude's discretion; centralizing them means one change updates all surfaces |

---

## Common Pitfalls

1. **Circular import between `recommendation/` and `intelligence/`:** `ValuationEngine` calls `apply_stabilization()` from `recommendation/anti_overreaction.py`. If `recommendation/card_engine.py` also imports from `intelligence/models.py`, there is a cycle. Resolution: `anti_overreaction.py` imports only `PlayerValue` from `intelligence.models` — a one-way dependency. `card_engine.py` takes `PlayerValue` and other module outputs as arguments, never importing from engine classes directly.

2. **FantasyCalc player ID mismatch:** FantasyCalc uses MFL IDs, not Sleeper IDs. A naïve player lookup by Sleeper ID will return no results. The `players` table must be extended with an `mfl_id` column, populated from the FantasyCalc response by name+position+team matching on first fetch, then cached.

3. **Stale market values in response:** `lens_market` depends on FantasyCalc data that is fetched once daily. If market ingest is skipped, all `model_vs_market_gap` computations will use stale or null values. The `FreshnessService` should track a `market_values` domain — same as it tracks `injuries`, `depth_chart` — so the router can surface a freshness warning when market data is >24h old.

4. **Priority rank collisions across modules:** The `priority = impact × confidence × execution × urgency` formula produces values in [0,1]. When cards from multiple modules are sorted together (e.g., in a dashboard), many cards may share the same raw score. Enforce that priority ranks are assigned as final integers only after all cards within a request scope are computed, using rank ordering on the raw float score before converting to int. Within a single module response, they should be 1-N ranked, not globally unique.

5. **`RecommendationCard` on optional vs. required field:** Some routers call engines lazily (e.g., `include_reroutes: bool = False` on `TradeRequest`). Cards should follow the same optional pattern: computed only when the response is requested with cards enabled, or always computed if the engine is fast enough. The `list[RecommendationCard] | None = None` pattern (matching existing `reroutes` and `package` fields on `TradeEvaluation`) avoids breaking changes.

6. **Context flag table scope vs. league scope:** Flags are player-scoped global (D-12), not league-scoped. The `player_context_flags` table has NO `league_id` column. This is intentional. If a player changes teams, all leagues using that player get the `team_change` flag. Enforce this in the schema to prevent accidentally scoping flags.

7. **Alembic migration numbering:** Migrations 015–020 are already in use. Phase 17 must start at 021. Check `backend/alembic/versions/` before assigning numbers. Confirmed current head: `020_expand_prospect_feature_columns.py`.

8. **`lens_market` rewrite backward compatibility:** `lens_market` is currently computed purely from model components (`market_liquidity`, `positional_scarcity`, `rerollability`) in `ValuationEngine`. Phase 17 changes this to incorporate external market data. Any existing test that hard-codes an expected `lens_market` value will break. Tests must be updated to either mock the market service or assert on range rather than exact value.

---

## Code Examples

### FantasyCalc Client Pattern (mirrors SleeperClient)

```python
# backend/src/fantasy/market/fantasycalc_client.py
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.NetworkError)

class FantasyCalcClient:
    BASE_URL = "https://api.fantasycalc.com"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "FantasyCalcClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception(_is_retriable),
        reraise=True,
    )
    async def fetch_values(
        self, is_dynasty: bool, num_qbs: int, num_teams: int, ppr: float
    ) -> list[dict]:
        response = await self._client.get(
            f"{self.BASE_URL}/values/current",
            params={
                "isDynasty": str(is_dynasty).lower(),
                "numQbs": num_qbs,
                "numTeams": num_teams,
                "ppr": ppr,
            },
        )
        response.raise_for_status()
        return response.json()
```

### Alembic Migration Template (Phase 17 — starts at 021)

```python
# backend/alembic/versions/021_recommendation_market_intelligence.py
revision = "021_recommendation_market_intelligence"
down_revision = "020_expand_prospect_feature_columns"

def upgrade() -> None:
    # player_context_flags — player-scoped, no league_id
    op.execute("""
        CREATE TABLE IF NOT EXISTS player_context_flags (
            id              INTEGER PRIMARY KEY,
            player_id       VARCHAR NOT NULL,
            flag_type       VARCHAR NOT NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at      TIMESTAMP,
            source          VARCHAR NOT NULL DEFAULT 'sleeper_ingest',
            metadata_json   VARCHAR,
            UNIQUE (player_id, flag_type)
        )
    """)
    # market_values — one row per player, updated daily
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_values (
            id                  INTEGER PRIMARY KEY,
            player_id           VARCHAR NOT NULL,
            fetched_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fantasycalc_value   FLOAT,
            fantasycalc_rank    INTEGER,
            fantasycalc_trend30 FLOAT,
            UNIQUE (player_id)
        )
    """)
    # recommendation_cards_cache — optional fast-read cache
    op.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_cards_cache (
            id              INTEGER PRIMARY KEY,
            league_id       VARCHAR NOT NULL,
            roster_id       INTEGER NOT NULL,
            module          VARCHAR NOT NULL,
            computed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cards_json      VARCHAR NOT NULL,
            UNIQUE (league_id, roster_id, module)
        )
    """)
    # players table extension for mfl_id
    op.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS mfl_id VARCHAR")
```

---

## External Market Data Source: FantasyCalc (Recommendation)

**Recommendation: FantasyCalc** (over KTC and Sleeper ADP baseline).

**Rationale:**
- KTC has no public API — all access is via web scraping. Fragile, against ToS. **Eliminated.**
- Sleeper ADP (`player_adp_baseline` table) is already in the project but is redraft-oriented and lacks dynasty-specific signals. It will serve as the fallback when FantasyCalc is unavailable.
- FantasyCalc provides a documented REST endpoint (`https://api.fantasycalc.com/values/current`) that powers their own website. It supports dynasty-specific parameters (`isDynasty=true`), `numQbs`, `numTeams`, `ppr`. Response includes `value` (dynasty trade value on a 0–11000 scale), `overallRank`, `positionRank`, and `trend30Day`. Verified live — HIGH confidence.

**Confidence: HIGH** — endpoint verified via direct API call.

---

## Manager-Demand Value Approach (D-17 Resolution)

**Recommendation: Extend Phase 12 approach.**

Phase 12 `ProfilingEngine._compute_value_delta()` already aggregates trade history per manager to compute pick premiums. The same `transactions` table is the source. The extension required for Phase 17:
- Generalize `_compute_value_delta` to operate on all players, not just picks
- For each player, aggregate leagues' trades to compute a per-player "implied market value" from revealed preferences (what people actually gave up to get this player)
- Expose this as `manager_demand_value` — a league-specific signal representing demand pressure

A new `per-player demand model` would require significantly more infrastructure (feature extraction, statistical model, inference pipeline) with no clear accuracy advantage over the simpler trade-history aggregation. The simpler extension is appropriate.

---

## Validation Architecture

### Acceptance Tests Required Per Major Capability

**1. RecommendationCard model shape (REC-01, REC-02)**
- Unit: `RecommendationCard` can be instantiated with all 15 required fields; Pydantic raises `ValidationError` if any required field is missing
- Unit: `SupportingFactor` validates `direction` as one of `positive/negative/neutral`; magnitude as one of `high/medium/low`
- Integration: `/trade/evaluate` response includes `recommendation_cards: list[...]` field; each card passes `RecommendationCard.model_validate()`

**2. Priority rank formula (REC-04)**
- Unit: `compute_priority(1.0, 1.0, 1.0, 1.0)` returns 1 (highest priority)
- Unit: `compute_priority(0.0, 1.0, 1.0, 1.0)` returns 100 (lowest priority)
- Unit: two cards with different raw scores produce distinct priority ranks

**3. Confidence contract (REC-03)**
- Unit: `confidence_label` is "HIGH" iff `confidence_score >= 0.75`, "MEDIUM" iff `>= 0.50`, "LOW" otherwise
- Integration: no card is emitted without a `what_would_change_this_call` value

**4. Anti-overreaction layer (REC-05)**
- Unit: `is_elite()` returns True only when all four composite thresholds are met
- Unit: bearish dampening — elite player with `comp_current_production=0.20` gets `comp_current_production` raised to `BEARISH_PRODUCTION_FLOOR` (0.40) when no context flags active
- Unit: bearish dampening is bypassed when `injury_recovery` or `role_compression` flag is active
- Unit: bullish dampening — non-elite player with `comp_ceiling=0.90` gets ceiling capped at `BULLISH_CEILING_CAP` (0.65)
- Integration: `ValuationEngine.compute_player()` output for a known-elite player with a one-year dip does not produce `lens_production < 0.40` without a context flag

**5. Player context flags (REC-06)**
- Unit: `FlagEngine.derive_flags(player_data)` — player with `depth_chart_order >= 2` produces `depth_chart_competition` flag
- Unit: `FlagEngine.derive_flags(player_data)` — player with `injury_status = "Out"` produces `injury_recovery` flag
- Unit: flag with `expires_at` in the past is not returned by `FlagRepo.get_active_flags(player_id)`
- Integration: player with an active context flag produces a `RecommendationCard` with at least one `supporting_factors` entry corresponding to the flag

**6. Parallel values / lens_market (MKT-01)**
- Unit: `PlayerValue` has fields `lens_production`, `lens_market`, `lens_insulation`, `lens_team_fit`, `lens_direction` — all five present
- Integration: after market ingest, `lens_market` differs from its pre-Phase-17 computation for at least one player with a FantasyCalc value

**7. Model-vs-market gap (MKT-02, MKT-03)**
- Unit: `MarketGapEngine.classify(gap=0.25, anti_overreaction_fired=False)` returns `"buy_low"`
- Unit: `MarketGapEngine.classify(gap=-0.25, anti_overreaction_fired=False)` returns `"sell_high"`
- Unit: `MarketGapEngine.classify(gap=0.05, anti_overreaction_fired=True)` returns `"hold_despite_weak_market"`
- Integration: player cards, trade recommendations, and lineup recommendations all include a populated `model_vs_market_gap` field for players with market data

**8. MKT-04 surface visibility**
- Integration: `/trade/evaluate` response — `TradeEvaluation.recommendation_cards` includes at least one card with a non-null `model_vs_market_gap` when market data is available for traded players
- Integration: `/intelligence/lineup/{league_id}/{roster_id}` — `LineupResult.recommendation_cards` includes at least one card with `model_vs_market_gap`
- Integration: `/intelligence/hygiene/{league_id}/{roster_id}` — `HygieneResult.recommendation_cards` similarly populated

**9. Hold-despite-weak-market (MKT-05)**
- Integration: a manufactured scenario where an elite player has `lens_market < 0.30` (weak market signal) triggers at least one `RecommendationCard` with `recommendation_type = "hold"` and gap classification `"hold_despite_weak_market"` — not `"sell_high"`

**10. FantasyCalc client**
- Unit (mocked): `FantasyCalcClient.fetch_values(is_dynasty=True, ...)` with a mocked `httpx.AsyncClient` returning a known fixture produces correct `ExternalPlayerValue` objects
- Unit: fetch failure (5xx) is retried up to 3 times; 4th failure raises and is caught by `MarketService` graceful fallback

**11. Alembic migration**
- Integration: migration 021 runs cleanly on a fresh DuckDB file; all three new tables exist; `players` table has `mfl_id` column; no conflict with 015–020

---

## Sources

- Sleeper API docs: https://docs.sleeper.com/ (player fields: `depth_chart_order`, `depth_chart_position`, `injury_status`, `status`, `news_updated`) — HIGH confidence
- FantasyCalc API: `https://api.fantasycalc.com/values/current` (verified live) — HIGH confidence
- FantasyCalc API intro article: https://www.fantasydatapros.com/fantasyfootball/blog/fantasycalc/1 — MEDIUM confidence (supplemental)
- KTC no public API: https://keeptradecut.com/frequently-asked-questions (FAQ confirms scraping only) — MEDIUM confidence via search confirmation
- Existing project code (primary sources — HIGH confidence):
  - `/backend/src/fantasy/intelligence/models.py` — `PlayerValue`, `TeamScorecard`, `DirectionResult`
  - `/backend/src/fantasy/intelligence/valuation_engine.py` — `ValuationEngine.compute_player()`
  - `/backend/src/fantasy/trade/models.py` — `TradeEvaluation`, `DimensionScore`, `StrategicDistinction`
  - `/backend/src/fantasy/lineup/models.py` — `LineupResult`, `HygieneResult`
  - `/backend/src/fantasy/waiver/models.py` — `WaiverRecommendation`, `ActionPlanItem`
  - `/backend/src/fantasy/profiling/profiling_engine.py` — `_compute_value_delta()`, `_load_trades()`
  - `/backend/src/fantasy/ingestion/sleeper_client.py` — `fetch_players()` existing pattern
  - `/backend/alembic/versions/` — confirmed 020 is current head; Phase 17 starts at 021
