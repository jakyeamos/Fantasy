# Phase 5: Trade Intelligence - Research

**Researched:** 2026-03-21
**Domain:** Trade evaluation engine, reroute path generation, package builder, FastAPI service layer, DuckDB analytical queries, React/shadcn frontend
**Confidence:** HIGH (architecture and stack — built directly on verified Phase 2/4 patterns), MEDIUM (scoring formula weights per dimension — derived from domain reasoning, not a single authoritative source)

---

## User Constraints

> Copied verbatim from 05-CONTEXT.md. Planner MUST honor these.

### Locked Decisions

**Trade input**
- D-01: Player-anchored input — user searches and adds players/picks freely to each side; not roster-browse-only
- D-02: Up to 3 parties supported — user assigns assets to each team's send/receive sides; evaluation always scores from the user's team perspective
- D-03: Pick identity matters — picks are entered as specific picks by owner (e.g., "Mike's 2026 1st"), not abstract tiers; projected draft slot is surfaced per pick
- D-04: Trade evaluator is launchable from multiple entry points: manager dossier, league drill-in, and standalone

**Evaluation output**
- D-05: No composite verdict — 7 sub-scores are shown; user forms their own conclusion
- D-06: Strategic vs. market-fair distinction (TRADE-04) is a prominent separate callout banner — not buried in a low direction-fit sub-score. Example: "Market fair — but moves you away from your rebuild"
- D-07: Low-confidence dimensions show an inline `(low confidence)` label with muted text color on the dimension row — not a separate caveat section
- D-08: Evaluation output has an explicit "See reroutes" affordance as the natural next action after reading scores

**Reroute paths**
- D-09: Two reroute types surfaced: (1) better-value target at the same position as the player being acquired, and (2) better package for the same target
- D-10: Maximum 3 reroutes — enough signal without noise
- D-11: Each reroute shows one-line reasoning explaining why it's a better option
- D-12: Reroutes live in a slide-in panel triggered by "See reroutes" — not a separate tab or page

**Package builder**
- D-13: Package builder is not a standalone tool — it is triggered from the trade evaluation screen after scoring
- D-14: Manager-specific personalization is the default output — Phase 4 manager profile is applied automatically; no toggle required
- D-15: Two distinct offer structures: aggressive open (what you could get away with) and fair close (genuinely balanced) — not a single midpoint
- D-16: Output is screen-readable only — user executes manually in Sleeper; no copy/export functionality needed

### Claude's Discretion

- Exact scoring formula per dimension (weights, normalization approach)
- How to handle trades where the counterparty is not in the user's league (hypothetical trades)
- Specific slide-in panel component choice (shadcn Sheet vs. custom drawer)
- How to display pick slot projections in the input (inline badge vs. tooltip)
- Route structure for the trade evaluator (e.g., `/league/:leagueId/trades/new` or standalone `/trades`)

### Deferred Ideas (out of scope — do not plan)

- Dynamic pick values in trade evaluation — Phase 6 replaces Phase 2 baseline pick values once standings-aware pick engine is built
- Manager-specific pitch notes as a standalone feature (TRADE-V2-01) — v2 backlog
- Saving/bookmarking evaluated trades for later review — not in Phase 5 scope
- Receiving an offer from Sleeper and auto-populating the evaluator — Sleeper API is read-only; manual input only

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRADE-01 | System evaluates any proposed trade on 7 dimensions: market fairness, roster fit, direction fit, timing quality, insulation gain/loss, liquidity gain/loss, and manager exploit quality — with confidence level per dimension | 7-dimension scoring engine documented in Architecture Patterns; confidence per dimension tied to data availability |
| TRADE-02 | System surfaces reroute paths: better targets for the same asset, 2-for-1/3-for-2 alternatives, pick-based versions of the move, tier-down options for insulation | Reroute generation pattern documented; two reroute types per D-09; max 3 per D-10 |
| TRADE-03 | System generates package builder: fair range, best version of the trade, and manager-specific opening offer structures | Package builder pattern documented; two-offer structure (aggressive open / fair close) per D-15; manager profile consumed automatically per D-14 |
| TRADE-04 | System distinguishes a market-fair but strategically mediocre trade from one that advances team direction | Strategic distinction banner pattern documented; direction fit dimension feeds the banner; always rendered per UI-SPEC |

---

## Summary

Phase 5 is a composition phase: it assembles outputs from Phase 2 (player values, direction labels, team scorecards) and Phase 4 (manager profiles, pitch angles) into a trade intelligence layer. No new external data sources are needed. All inputs exist in DuckDB tables established by prior phases.

The backend adds a `fantasy/trade/` package following the established `intelligence/` and `profiling/` package layouts. It contains a `TradeEngine` class that runs the 7-dimension evaluation, a `RerouteEngine` that generates alternative trade paths, and a `PackageBuilder` that applies the manager profile to produce two offer structures. A new `/trade` FastAPI router wires these engines with a single POST endpoint.

The frontend adds a `TradeEvaluatorPage` with three sub-components: `TradeInputPanel` (3-party asset input), `EvaluationOutputPanel` (7 dimension rows + strategic banner), and `PackageBuilderPanel` (two offer cards). The reroute sheet uses shadcn `Sheet` per the UI-SPEC. The page is reachable from three entry points.

The most important architectural decision is how to compute the 7 dimension scores. The approach is deterministic formula-based scoring — the same design philosophy as Phase 2's scorecard engine. Each dimension reads from already-computed Phase 2/4 tables and applies a formula. Dimension confidence is a function of data completeness (more trade history and more player data = higher confidence). No ML, no training.

---

## Standard Stack

### Core (inherited — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | Read player_values, team_directions, manager_profiles; write trade_evaluations | Locked stack; analytical SQL aggregations on existing Phase 2/4 tables |
| pydantic | 2.x | TradeRequest, TradeEvaluation, RerouteResult, PackageOffer domain models | Established Phase 1–4 pattern; type safety across layers |
| fastapi | 0.115.x | POST /trade/evaluate, GET /trade/players/search, GET /trade/picks/search | Established Phase 1–4 pattern |
| polars | 1.x | Asset comparison aggregation during reroute generation | Already in stack; efficient for multi-column player value comparisons |

### Frontend (inherited — new shadcn components only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| shadcn/ui (sheet) | current | RerouteSheet slide-in panel | Locked per UI-SPEC; Radix Dialog under the hood, accessible |
| shadcn/ui (input) | current | Player/pick search text field | Locked per UI-SPEC |
| shadcn/ui (command) | current | Combobox autocomplete for player/pick search | Locked per UI-SPEC |
| shadcn/ui (popover) | current | Anchor for Command dropdown | Locked per UI-SPEC |
| shadcn/ui (scroll-area) | current | Scrollable asset list in party columns | Locked per UI-SPEC |
| TanStack Query | 5.x | Async state for evaluate mutation, player search | Inherited Phase 3–4 pattern |
| TanStack Router | 1.x | New trade evaluator route | Inherited Phase 3–4 pattern |

### No New Backend Installs

No new Python packages are required. The full computation stack is present from Phases 1–4. Do not add scikit-learn, numpy, or pandas.

**Phase 5 shadcn installs:**
```bash
npx shadcn@latest add sheet input command popover scroll-area
```

---

## Architecture Patterns

### Backend Package Structure

```
backend/src/fantasy/
├── trade/                         # NEW — Phase 5 engines
│   ├── __init__.py
│   ├── constants.py               # Dimension weights, confidence thresholds, reroute config
│   ├── models.py                  # TradeRequest, TradeEvaluation, DimensionScore, RerouteResult, PackageOffer
│   ├── trade_engine.py            # 7-dimension evaluation engine
│   ├── reroute_engine.py          # Reroute path generator
│   ├── package_builder.py         # Two-offer package builder (aggressive open / fair close)
│   └── trade_repo.py             # DuckDB reads from player_values, team_directions, manager_profiles
├── routers/
│   ├── trade.py                   # NEW — POST /trade/evaluate, GET /trade/players/search, GET /trade/picks/search
│   └── ... (existing routers)
└── main.py                        # app.include_router(trade_router) added
```

### Frontend Structure

```
src/
├── routes/
│   └── trades.tsx                 # NEW — TradeEvaluatorPage (or league.$leagueId.trades.new.tsx)
├── components/trade/
│   ├── TradeInputPanel.tsx        # 3-party asset input grid
│   ├── AssetChip.tsx              # Player/pick chip with remove affordance
│   ├── EvaluationOutputPanel.tsx  # Strategic banner + 7 dimension rows + action buttons
│   ├── StrategicDistinctionBanner.tsx  # The most important output — amber callout
│   ├── DimensionScoreRow.tsx      # One dimension row with score bar + confidence label
│   ├── RerouteSheet.tsx           # shadcn Sheet — slide-in reroute panel
│   └── PackageBuilderPanel.tsx    # Two offer cards in-page expansion
```

### Pattern 1: TradeEngine — 7-Dimension Evaluation

**What:** The `TradeEngine` accepts a `TradeRequest` (assets on each side, league context, user's roster_id) and returns a `TradeEvaluation` with 7 `DimensionScore` objects. Each dimension score is a float (0–100) plus a confidence level (HIGH/MEDIUM/LOW) and a one-line reasoning string.

**When to use:** Always called synchronously on POST /trade/evaluate. Results are not persisted — evaluation is stateless and re-runnable.

**Design:**
```python
# fantasy/trade/trade_engine.py
from fantasy.trade.models import TradeRequest, TradeEvaluation, DimensionScore
from fantasy.trade.trade_repo import TradeRepo

class TradeEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._repo = TradeRepo(conn)

    def evaluate(self, request: TradeRequest) -> TradeEvaluation:
        # Gather Phase 2/4 data for all assets in the trade
        sending_values = self._repo.get_player_values(
            request.user_sends, request.league_id, request.user_roster_id
        )
        receiving_values = self._repo.get_player_values(
            request.user_receives, request.league_id, request.user_roster_id
        )
        direction = self._repo.get_team_direction(request.league_id, request.user_roster_id)
        manager_profile = self._repo.get_manager_profile(
            request.league_id, request.counterparty_roster_id
        )

        return TradeEvaluation(
            market_fairness=self._score_market_fairness(sending_values, receiving_values),
            roster_fit=self._score_roster_fit(receiving_values, request, direction),
            direction_fit=self._score_direction_fit(sending_values, receiving_values, direction),
            timing_quality=self._score_timing_quality(sending_values, receiving_values),
            insulation_delta=self._score_insulation_delta(sending_values, receiving_values),
            liquidity_delta=self._score_liquidity_delta(sending_values, receiving_values),
            manager_exploit_quality=self._score_manager_exploit(sending_values, receiving_values, manager_profile),
            strategic_distinction=self._compute_strategic_distinction(direction),
        )
```

**Key insight:** Each dimension reads from already-computed Phase 2 `player_values` and `team_directions` rows. The TradeEngine does not recompute player values — it reads the pre-computed `comp_*` and `lens_*` fields from the `player_values` table. This makes evaluation fast (DuckDB reads) rather than expensive (full re-valuation).

### Pattern 2: 7-Dimension Scoring Formulas

**Confidence:** MEDIUM — formulas are domain-reasoned, not empirically validated. The planner should treat specific weights as starting points, not locked values.

| Dimension | Primary Input Fields | Formula Logic | Confidence Signal |
|-----------|---------------------|---------------|-------------------|
| Market Fairness | `lens_market` per asset on both sides | Sum of market lens values received vs. sent; delta normalized to 0–100 (50 = perfectly fair) | HIGH if both sides have market lens values; LOW if any pick or rookie with no market data |
| Roster Fit | `comp_positional_scarcity`, `lens_team_fit` for received assets | Average team-fit lens of received assets; bonus if received assets fill a positional need gap in user's roster | MEDIUM — team-fit lens requires knowing user's lineup slots |
| Direction Fit | `lens_direction` for sent and received assets vs. `primary_label` from `team_directions` | Net direction-lens delta (received direction value − sent direction value); positive = advancing | HIGH if direction label is HIGH confidence; LOW if direction label is LOW confidence |
| Timing Quality | `comp_age_curve`, `comp_short_term` for all assets | Trade younger rising assets at a premium vs. older declining ones; penalize selling peak-age assets at a discount | MEDIUM — timing is inherently uncertain; age curve data from Phase 2 |
| Insulation Gain/Loss | `comp_insulation`, `lens_insulation` per asset | Net insulation lens delta; insulation loss = giving up roster insurance | MEDIUM |
| Liquidity Gain/Loss | `comp_market_liquidity` per asset | Net market liquidity of received vs. sent assets; gains in liquidity = flexibility | HIGH if market data available |
| Manager Exploit Quality | `exploitability_score`, `exploitation_type`, `pitch_angles` from `manager_profiles` | Score how well this specific trade targets the counterparty's documented weakness; zero if no profile or low confidence | LOW if evidence_count < MIN_TRADE_EVIDENCE_THRESHOLD (10); MEDIUM otherwise |

**Normalization:** All scores normalized to 0–100. 50 is neutral (fair/even). Scores above 50 favor the user; below 50 disfavor the user. Market fairness is the only symmetric dimension — all others are direction-aware.

**Per-dimension confidence rules:**
```python
# fantasy/trade/constants.py

DIMENSION_CONFIDENCE_RULES = {
    "market_fairness": lambda data: "HIGH" if data.all_have_market_lens else "LOW",
    "roster_fit": lambda data: "HIGH" if data.team_fit_available else "MEDIUM",
    "direction_fit": lambda data: (
        "HIGH" if data.direction_confidence > 0.7
        else "MEDIUM" if data.direction_confidence > 0.4
        else "LOW"
    ),
    "timing_quality": lambda data: "MEDIUM",  # Always medium — inherently uncertain
    "insulation_delta": lambda data: "MEDIUM",
    "liquidity_delta": lambda data: "HIGH" if data.all_have_market_lens else "MEDIUM",
    "manager_exploit_quality": lambda data: (
        "LOW" if data.manager_evidence_count < MIN_EXPLOIT_EVIDENCE_THRESHOLD
        else "MEDIUM"
    ),
}
```

### Pattern 3: Strategic Distinction Computation

**What:** A separate output computed alongside the 7 dimensions. Not a dimension itself — a banner that synthesizes market_fairness and direction_fit into a human-readable verdict.

**Three states:**
- **Strategically negative:** market_fairness >= 40 (within 10 points of fair) AND direction_fit < 45 — "Market fair — but moves you away from your [label]"
- **Strategically advancing:** market_fairness >= 40 AND direction_fit > 55 — "Market fair — and advances your [label]"
- **Strategically neutral:** market_fairness >= 40 AND direction_fit between 45–55 — "Market fair — no directional impact"
- **Unfair trade (additional):** market_fairness < 40 — banner shifts to reflect that the trade is both unfair and directionally wrong/right

**Design:**
```python
# fantasy/trade/trade_engine.py
def _compute_strategic_distinction(
    self,
    market_fairness: DimensionScore,
    direction_fit: DimensionScore,
    direction_label: str,
) -> StrategicDistinction:
    market_fair = market_fairness.score >= 40
    direction_advancing = direction_fit.score > 55
    direction_negative = direction_fit.score < 45

    if market_fair and direction_advancing:
        verdict = "advancing"
        headline = f"Market fair — and advances your {direction_label.replace('_', ' ')}"
    elif market_fair and direction_negative:
        verdict = "negative"
        headline = f"Market fair — but moves you away from your {direction_label.replace('_', ' ')}"
    else:
        verdict = "neutral"
        headline = "Market fair — no directional impact"

    return StrategicDistinction(verdict=verdict, headline=headline)
```

### Pattern 4: RerouteEngine — Two Reroute Types

**What:** The `RerouteEngine` generates up to 3 alternative trade paths after the initial evaluation. Two types per D-09: (1) better-value target at the same position, (2) better package for the same target.

**Type 1 — Better target at the same position:**
- Identify the primary player being acquired from the user's receive side
- Query `player_values` for all players at the same position owned by the counterparty's roster that the user does NOT already own
- Rank by `lens_direction` (direction-fit lens for user's team) and `lens_market` combined
- Return the top 1–2 with one-line reasoning: "Higher direction-fit at the same position — {name} scores {X} vs. {Y}'s {Z}"

**Type 2 — Better package for the same target:**
- Keep the target player fixed
- Query what combination of user's assets would produce a fairer or more favorable market_fairness score
- Compare user's `lens_market` values across roster to find a cheaper package
- Return 1 alternative: "This package gets you {target} for less" or "Add a {round} pick instead of {player} to reduce overpay"

**Design:**
```python
# fantasy/trade/reroute_engine.py
class RerouteEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._repo = TradeRepo(conn)

    def generate(self, request: TradeRequest, evaluation: TradeEvaluation) -> list[RerouteResult]:
        reroutes = []

        # Type 1: better target at same position
        primary_target = self._identify_primary_target(request)
        if primary_target:
            better_targets = self._find_better_targets(
                primary_target, request.counterparty_roster_id,
                request.league_id, request.user_roster_id
            )
            reroutes.extend(better_targets[:2])  # max 2 of this type

        # Type 2: better package for same target
        if primary_target and len(reroutes) < 3:
            better_package = self._find_better_package(primary_target, request, evaluation)
            if better_package:
                reroutes.append(better_package)

        return reroutes[:3]  # D-10: max 3 total
```

### Pattern 5: PackageBuilder — Two-Offer Structure

**What:** Triggered from the evaluation screen after scoring. Reads the manager profile automatically and produces two offers: aggressive open (undervalue the counterparty's assets or overvalue your own) and fair close (genuinely balanced market value).

**Manager profile application (D-14):**
- `exploitation_type` from `manager_profiles` determines the aggressive offer shape
  - `value-loss trader`: open aggressively — they typically accept below-market value
  - `timing-error trader`: time the offer to exploit a recent loss or injury bounce
  - `directionally-incoherent trader`: offer assets that contradict their stated direction (they won't notice)
  - `archetype-specific overpayer`: include the asset type they overpay for in your receive side
- `pitch_angles` from `manager_pitch_angles` provides the specific archetype label and what to send/avoid

**Design:**
```python
# fantasy/trade/package_builder.py
class PackageBuilder:
    def build(
        self,
        request: TradeRequest,
        evaluation: TradeEvaluation,
        manager_profile: ManagerProfile,
    ) -> PackageBuilderResult:
        fair_value = self._compute_fair_package(request, evaluation)

        # Aggressive: bias the offer using manager's exploitation type
        aggressive = self._apply_manager_bias(fair_value, manager_profile)

        return PackageBuilderResult(
            aggressive_open=aggressive,
            fair_close=fair_value,
        )
```

### Pattern 6: API Contract

**POST /trade/evaluate** — main evaluation endpoint
```python
# Request
class TradeRequest(BaseModel):
    league_id: str
    user_roster_id: int
    counterparty_roster_id: int | None  # None for hypothetical trades
    user_sends: list[TradeAsset]        # players + picks
    user_receives: list[TradeAsset]
    third_party_trades: list[ThirdPartyTrade] | None  # D-02: up to 1 additional party
    include_reroutes: bool = False
    include_package: bool = False

class TradeAsset(BaseModel):
    asset_type: Literal["player", "pick"]
    player_id: str | None           # if player
    pick_owner_roster_id: int | None  # if pick — D-03: specific pick by owner
    pick_year: int | None
    pick_round: int | None
    projected_slot: str | None      # e.g. "1.04" — surfaced from traded_picks table

# Response
class TradeEvaluation(BaseModel):
    market_fairness: DimensionScore
    roster_fit: DimensionScore
    direction_fit: DimensionScore
    timing_quality: DimensionScore
    insulation_delta: DimensionScore
    liquidity_delta: DimensionScore
    manager_exploit_quality: DimensionScore
    strategic_distinction: StrategicDistinction
    reroutes: list[RerouteResult] | None     # populated if include_reroutes=True
    package: PackageBuilderResult | None     # populated if include_package=True

class DimensionScore(BaseModel):
    score: float          # 0–100; 50 = neutral
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: str        # one-line human-readable explanation
```

**GET /trade/players/search** — player autocomplete for trade input
```python
# Query params: league_id, q (search string), roster_id (optional — filter to one team)
# Returns: list of {player_id, full_name, position, team, roster_id, roster_name}
# Source: queries players table + rosters table
```

**GET /trade/picks/search** — pick autocomplete for trade input
```python
# Query params: league_id, roster_id (optional)
# Returns: list of {pick_owner_roster_id, pick_owner_name, year, round, projected_slot}
# Source: queries traded_picks table + rosters table; projected_slot from standings data
```

### Pattern 7: Alembic Migration for Trade Tables

Phase 5 does not persist trade evaluations (they are stateless). The only migration needed is for the `trade` router registration — no new DuckDB tables. However, a migration number must be reserved. Phase 5 is Alembic migration `006` (assuming Phase 3 used `005` and Phase 4 used — check actual migration count from prior phases before numbering).

**Current migrations verified:**
- `001_initial_schema.py` — Phase 1
- `002_add_player_stats_weekly.py` — Phase 1
- `003_add_adp_baseline.py` — Phase 1
- Phase 2 planned `004_phase2_output_tables.py`
- Phase 3/4 will add `005`, `006` for manager profile tables

Phase 5 trade evaluations are NOT persisted — evaluation is stateless (no new table migration needed). The `/trade` router simply plugs into `main.py` without schema changes.

### Pattern 8: Entry Point Wiring (Phases 3 and 4 Updates)

Per D-04 and UI-SPEC, three existing pages need "Evaluate Trade" button additions:

| Page | File | Change |
|------|------|--------|
| League drill-in | `src/routes/league.$leagueId.tsx` | Add `Button variant="outline"` labeled "Evaluate Trade" in page header; links to trade evaluator route |
| Manager dossier | `src/routes/league.$leagueId.managers.$managerId.tsx` | Add `Button variant="outline"` labeled "Evaluate Trade" in dossier header, next to manager name |
| Standalone | New route | `src/routes/trades.tsx` — new route, no existing page update |

### Anti-Patterns to Avoid

- **Recomputing player values inside the trade engine:** The TradeEngine reads from `player_values` table — it does NOT invoke ValuationEngine. Recomputing 12 components per player per trade evaluation is too expensive. Phase 2 pre-computes; Phase 5 reads.
- **Treating picks as abstract tiers:** D-03 is explicit — picks are specific picks by owner. The search endpoint returns specific `traded_picks` rows (owner, year, round). Abstract "2026 1st" is not a valid input.
- **Building a composite verdict:** D-05 forbids a composite score. The API must NOT return a single "trade score" — only 7 dimension scores. The frontend must NOT combine them into a rating.
- **Hiding or burying the strategic distinction banner:** D-06 and UI-SPEC are explicit — the banner is the first element in EvaluationOutputPanel and always rendered after evaluation runs. Do not make it dismissable or conditional on a good/bad score.
- **Making the package builder standalone:** D-13 is explicit — the package builder is triggered from the evaluation screen, not a standalone tool. The route for the package builder is the same trade evaluator route; it expands in-page.
- **Firing player search on every keystroke:** Debounce at 300ms per UI-SPEC Note 5.
- **Rendering EvaluationOutputPanel before first evaluation:** Per UI-SPEC Note 6 — use `null` return (not `opacity-0` or `invisible`). The panel does not exist in the DOM before the first successful evaluation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Player/pick autocomplete search with keyboard navigation | Custom combobox | shadcn `Command` + `Popover` | Radix handles focus trap, keyboard navigation, ARIA — essential for accessibility; Command is already planned (UI-SPEC) |
| Side panel for reroutes | Custom drawer | shadcn `Sheet` (side="right") | Radix Dialog under the hood, handles focus management, backdrop, escape key — already locked in UI-SPEC |
| Market value comparison | Custom valuation | Read `lens_market` from `player_values` | Phase 2 already computed this; re-implementing creates inconsistency |
| Direction fit scoring | Custom direction lookup | Read `primary_label` + `lens_direction` from `team_directions` and `player_values` | Phase 2 already did the direction classification; re-implementing creates divergence |
| Manager personalization logic | Custom manager behavior analysis | Read `manager_profiles` + `manager_pitch_angles` from Phase 4 tables | Phase 4 already profiled every manager; the package builder consumes, does not re-derive |
| Scrollable asset list with overflow control | `overflow-y: auto` CSS | shadcn `ScrollArea` | Radix handles cross-browser scrollbar styling consistently; locked in UI-SPEC |

---

## Code Examples

### TradeRepo: Reading Phase 2/4 Data

```python
# fantasy/trade/trade_repo.py
import duckdb
from typing import Sequence

class TradeRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_player_values(
        self, player_ids: Sequence[str], league_id: str, roster_id: int
    ) -> list[dict]:
        """Read pre-computed player_values rows for a list of player IDs."""
        placeholders = ", ".join("?" * len(player_ids))
        return self._conn.execute(
            f"""
            SELECT player_id, comp_insulation, comp_market_liquidity, comp_age_curve,
                   comp_positional_scarcity, lens_market, lens_insulation, lens_team_fit,
                   lens_direction, lens_production
            FROM player_values
            WHERE league_id = ?
              AND roster_id = ?
              AND player_id IN ({placeholders})
            """,
            [league_id, roster_id, *player_ids],
        ).fetchall()

    def get_team_direction(self, league_id: str, roster_id: int) -> dict:
        """Read team_directions row for the user's team."""
        row = self._conn.execute(
            """
            SELECT primary_label, confidence, approved_moves, discouraged_moves
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        return dict(row) if row else {}

    def get_manager_profile(self, league_id: str, roster_id: int) -> dict | None:
        """Read manager_profiles row for the counterparty."""
        row = self._conn.execute(
            """
            SELECT exploitability_score, exploitation_type_primary, exploitation_type_secondary,
                   evidence_count
            FROM manager_profiles
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        return dict(row) if row else None

    def search_players(self, league_id: str, q: str, roster_id: int | None = None) -> list[dict]:
        """Player search for trade input autocomplete — D-01."""
        roster_filter = "AND r.roster_id = ?" if roster_id else ""
        params = [league_id, f"%{q}%", f"%{q}%"]
        if roster_id:
            params.append(roster_id)
        return self._conn.execute(
            f"""
            SELECT p.player_id, p.full_name, p.position, r.roster_id
            FROM players p
            JOIN rosters r ON p.player_id = ANY(r.players)
            WHERE r.league_id = ?
              AND (p.full_name ILIKE ? OR p.position ILIKE ?)
              {roster_filter}
            LIMIT 20
            """,
            params,
        ).fetchall()

    def get_picks_for_league(self, league_id: str, roster_id: int | None = None) -> list[dict]:
        """Pick search for trade input — D-03: returns specific picks by owner."""
        roster_filter = "AND owner_id = ?" if roster_id else ""
        params = [league_id]
        if roster_id:
            params.append(roster_id)
        return self._conn.execute(
            f"""
            SELECT tp.roster_id as original_owner_id, tp.owner_id as current_owner_id,
                   tp.season as pick_year, tp.round
            FROM traded_picks tp
            WHERE tp.league_id = ?
              {roster_filter}
            ORDER BY tp.season, tp.round
            """,
            params,
        ).fetchall()
```

### Router Registration

```python
# backend/src/fantasy/main.py — addition only
from fantasy.routers.trade import router as trade_router
app.include_router(trade_router, prefix="/trade", tags=["trade"])
```

```python
# backend/src/fantasy/routers/trade.py
from fastapi import APIRouter, Depends
import duckdb
from fantasy.routers.deps import get_db
from fantasy.trade.trade_engine import TradeEngine
from fantasy.trade.reroute_engine import RerouteEngine
from fantasy.trade.package_builder import PackageBuilder
from fantasy.trade.models import TradeRequest, TradeEvaluation

router = APIRouter()

@router.post("/evaluate", response_model=TradeEvaluation)
async def evaluate_trade(
    request: TradeRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
):
    engine = TradeEngine(conn)
    evaluation = engine.evaluate(request)

    if request.include_reroutes:
        reroute_engine = RerouteEngine(conn)
        evaluation.reroutes = reroute_engine.generate(request, evaluation)

    if request.include_package:
        builder = PackageBuilder(conn)
        evaluation.package = builder.build(request, evaluation)

    return evaluation
```

### TanStack Query — Evaluate Mutation

```typescript
// src/hooks/useTradeMutation.ts
import { useMutation } from "@tanstack/react-query";

export function useTradeEvaluation() {
  return useMutation({
    mutationFn: async (request: TradeRequest) => {
      const res = await fetch("/trade/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      if (!res.ok) throw new Error("Evaluation failed");
      return res.json() as Promise<TradeEvaluation>;
    },
  });
}
```

### Player Search — Debounced Command

```typescript
// src/components/trade/PlayerSearchCommand.tsx
import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Command, CommandInput, CommandList, CommandItem } from "@/components/ui/command";

// Debounce 300ms per UI-SPEC Note 5
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function PlayerSearchCommand({ leagueId, onSelect }) {
  const [q, setQ] = useState("");
  const debouncedQ = useDebounce(q, 300);

  const { data, isLoading } = useQuery({
    queryKey: ["players", leagueId, debouncedQ],
    queryFn: () =>
      fetch(`/trade/players/search?league_id=${leagueId}&q=${debouncedQ}`)
        .then((r) => r.json()),
    enabled: debouncedQ.length >= 2,
  });

  return (
    <Command>
      <CommandInput
        placeholder="Search players or picks..."
        value={q}
        onValueChange={setQ}
      />
      <CommandList>
        {isLoading && <Skeleton className="h-8 w-full" />}
        {data?.map((p) => (
          <CommandItem key={p.player_id} onSelect={() => onSelect(p)}>
            {p.full_name} — {p.position}
          </CommandItem>
        ))}
        {!isLoading && data?.length === 0 && (
          <p className="py-2 text-center text-sm text-muted-foreground">
            No players found.
          </p>
        )}
      </CommandList>
    </Command>
  );
}
```

---

## Common Pitfalls

### 1. Pick valuation falls back to Phase 6 scope
**Trap:** Attempting to compute dynamic pick values (standings-adjusted) inside Phase 5. Phase 6 owns dynamic pick valuation.
**Prevention:** Use `comp_market_liquidity` from the `player_values` table for picks, or use the `ROUND_WEIGHTS` constant from Phase 2 (`{1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}`) as a static baseline. Do not build a standings-aware pick algorithm — that is explicitly deferred to Phase 6.

### 2. Missing player_values rows (undrafted players, just-added players)
**Trap:** A player added to the trade input may not have a `player_values` row if Phase 2 hasn't computed values for them (e.g., a player not on any league roster, a new signing after last ingest).
**Prevention:** TradeEngine must handle missing `player_values` rows gracefully. Any missing asset lowers the confidence of its dimension to LOW. Never propagate None/NaN — use safe defaults (lens values default to 0.5 for neutral; flag confidence as LOW for that dimension).

### 3. counterparty_roster_id is None (hypothetical trades)
**Trap:** User evaluates a trade with a non-leaguemate or an unspecified counterparty. `manager_exploit_quality` dimension has no data source.
**Prevention:** When `counterparty_roster_id` is None, `manager_exploit_quality` scores 50 (neutral) with confidence LOW and reasoning "No counterparty profile available." All other dimensions compute normally from player_values.

### 4. Evaluation output renders before data is loaded
**Trap:** Frontend renders `EvaluationOutputPanel` with undefined/null data during the mutation's pending state, producing UI flicker or broken skeleton.
**Prevention:** Per UI-SPEC Note 6 — `EvaluationOutputPanel` is null-returned before the first evaluation. During the evaluation mutation in-flight, render the skeleton layout (not null). Use `mutation.isPending` to show skeleton, `mutation.data` existence to show results.

### 5. Third-party trade evaluation scoring confusion
**Trap:** With 3 parties, assets flow in multiple directions. The evaluation must always score from the user's perspective (D-02), not from a global fairness standpoint.
**Prevention:** `TradeRequest` always has a `user_roster_id`. All 7 dimensions score relative to the user's team's net position: what the user's team sends out minus what the user's team receives, regardless of the third party's role. Third-party assets that don't touch the user's team are ignored in scoring.

### 6. "Build Package" button visible before evaluation runs
**Trap:** "Build Package" and "See reroutes" buttons are part of `EvaluationOutputPanel` — they must not be accessible before evaluation completes.
**Prevention:** Both buttons are part of the null-guarded `EvaluationOutputPanel` — they don't exist in the DOM pre-evaluation. No separate visibility management needed.

### 7. Strategic distinction banner using Alert component
**Trap:** Using shadcn `Alert` for the strategic distinction banner creates visual confusion with Phase 4's LOW CONFIDENCE Alert.
**Prevention:** Per UI-SPEC Note 2 — the strategic banner is a custom `div` with `border-l-4` left-bar treatment, not shadcn `Alert`. The LOW CONFIDENCE Alert (Phase 4) uses a square box; the strategic banner uses a left bar. They must look visually distinct.

### 8. Alembic migration numbering collision
**Trap:** Phase 5 plans a new migration number that collides with Phase 3 or Phase 4 migrations.
**Prevention:** Phase 5 trade evaluation is stateless — no new DuckDB tables. No Alembic migration is needed for Phase 5. Verify actual migration count from backend/alembic/versions/ before any executor writes a migration file.

---

## Integration Points Summary

| Data Needed | Source Table | Phase Built | Query Pattern |
|-------------|-------------|-------------|---------------|
| Player market value | `player_values.lens_market` | Phase 2 | Read by player_id + league_id + roster_id |
| Player direction value | `player_values.lens_direction` | Phase 2 | Read by player_id + league_id + roster_id |
| Player insulation | `player_values.comp_insulation`, `lens_insulation` | Phase 2 | Same |
| Player liquidity | `player_values.comp_market_liquidity` | Phase 2 | Same |
| Team direction label | `team_directions.primary_label`, `confidence` | Phase 2 | Read by league_id + roster_id |
| Team approved moves | `team_directions.approved_moves` | Phase 2 | Same |
| Manager exploitability | `manager_profiles.exploitability_score`, `exploitation_type_primary` | Phase 4 | Read by league_id + roster_id |
| Manager pitch angles | `manager_pitch_angles.archetype_label`, `what_to_send`, `what_to_avoid` | Phase 4 | Read by league_id + roster_id |
| Pick ownership | `traded_picks.owner_id`, `season`, `round` | Phase 1 | Read by league_id |
| Player roster membership | `rosters.players` (JSON array) | Phase 1 | Used for search filtering |

---

## Validation Architecture

### Backend tests

| Test file | Tests |
|-----------|-------|
| `test_trade_engine.py` | `test_all_7_dimensions_present`, `test_scores_in_range`, `test_missing_player_values_confidence_low`, `test_no_composite_score`, `test_hypothetical_trade_manager_exploit_neutral` |
| `test_reroute_engine.py` | `test_max_3_reroutes`, `test_better_target_type_present`, `test_better_package_type_present`, `test_reroute_has_reasoning` |
| `test_package_builder.py` | `test_two_offer_structures_present`, `test_aggressive_open_distinct_from_fair_close`, `test_manager_profile_applied` |
| `test_trade_router.py` | `test_evaluate_endpoint_returns_200`, `test_evaluate_without_reroutes`, `test_evaluate_with_reroutes`, `test_player_search_endpoint`, `test_pick_search_endpoint` |

### Frontend verification

| Behavior | Verification |
|----------|-------------|
| EvaluationOutputPanel absent before evaluation | Inspect DOM: no `data-testid="evaluation-output"` before first button click |
| Strategic banner always present after evaluation | All 3 banner states render — covering strategically-negative, advancing, and neutral trades |
| Low confidence dimension row shows `(low confidence)` | Trigger a trade with a player missing from `player_values` — verify muted styling |
| "See reroutes" Sheet opens from right | Verify `Sheet` slides in from right, does not navigate away |
| Package builder expands in-page (not a modal) | Verify `PackageBuilderPanel` appears below `EvaluationOutputPanel` in the same scroll context |
| Player search debounced at 300ms | Confirm no API call fires until 300ms after keystroke stops |

---

*Phase: 05-trade-intelligence*
*Research completed: 2026-03-21*
