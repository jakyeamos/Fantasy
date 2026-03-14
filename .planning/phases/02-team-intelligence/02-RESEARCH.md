# Phase 2: Team Intelligence - Research

**Researched:** 2026-03-14
**Domain:** Dynasty fantasy football scoring engines, player valuation, direction classification, FastAPI service layer, DuckDB analytical queries
**Confidence:** HIGH (architecture and stack), MEDIUM (scoring formula constants — empirically derived from domain research but not from a single authoritative source)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEAM-01 | System generates a team scorecard with 9 decomposed sub-scores: win-now, future value, depth, pick capital, flexibility, fragility, age risk, liquidity, positional insulation | Sub-score computation formulas documented in Architecture Patterns section; DuckDB queries against Phase 1 tables identified |
| TEAM-02 | System detects and recommends a primary team direction from 8 options: true contender, fragile contender, fringe playoff, productive struggle, one-year punt, retool, elite value accumulation, hard rebuild | Rule-based classification engine design documented; input signals mapped; threshold approach described |
| TEAM-03 | System provides confidence score, reasoning, and 2+ alternate viable directions for every direction recommendation; includes what would materially alter the label | Confidence computation pattern described; alternate-viable design documented; delta threshold pattern for "what would change this" |
| TEAM-04 | System surfaces direction implications: which valuation weights change, which move types are approved, which are discouraged | Weight matrix design documented per direction label; approved/discouraged move type catalog defined |
| TEAM-05 | System generates ranked move recommendations per team: top move types to execute and types to avoid given current direction and roster | Move recommendation engine design — maps direction label + sub-score gaps to ranked action list |
| PLAY-01 | System generates player values with 12 decomposed component scores: current production, short-term utility, role stability, age curve/decline risk, insulation value, market liquidity, positional scarcity, fragility/injury risk, ceiling, floor stability, rerollability, contract security proxy | Component computation sources documented; age curve constants sourced from ESPN/FantasyPoints research |
| PLAY-02 | System reweights player values by league-specific format (scoring system, lineup requirements, positional scarcity in this league) | Format adjustment layer design documented; PPR/superflex/TEP multiplier patterns identified |
| PLAY-03 | System reweights player values by team direction (same player has materially different value on a rebuild vs. contending team) | Direction-weight matrix documented per direction label; implementation pattern described |
| PLAY-04 | User can view a player across 5 simultaneous value lenses: production, market, insulation, team-fit, and direction-specific | Response schema design documented; lens aggregation pattern described |
</phase_requirements>

---

## Summary

Phase 2 is a pure computation phase: consume the ingested data from Phase 1 tables and run three interconnected engines — the Team Scorecard Engine (TEAM-01), the Direction Detection Engine (TEAM-02/03/04/05), and the Player Valuation Engine (PLAY-01/02/03/04). No new external API calls are needed. All inputs come from DuckDB tables built in Phase 1.

The architecture follows the same adapter-first service-layer pattern established in Phase 1. The three engines live in a new `fantasy/intelligence/` package and are consumed by new FastAPI routers. They read from `LeagueRepo` (or direct DuckDB queries) and write computed results to new Phase 2 output tables. All engine outputs are Pydantic domain models; routers never touch engine internals.

The core design decision for the Direction Detection Engine is **rule-based classification, not machine learning**. The dataset is small (a dynasty league has 8-16 teams), the rules are well-defined and expert-specifiable, and the outputs must be explainable with human-readable reasoning. A decision tree or logistic regression model trained on 10 teams is not meaningful. A rule engine with weighted signal thresholds is the correct approach — it produces the reasoning strings and alternate-viable outputs required by TEAM-03 without a training dataset.

Player valuation (PLAY-01) similarly uses deterministic formula engines, not learned models. The 12 component scores are computed from ingested stats and metadata, then normalized within the league context. Phase 8 will apply backtested models; Phase 2 provides the formula foundation.

**Primary recommendation:** Build three engine classes in `fantasy/intelligence/` (ScorecardEngine, DirectionEngine, ValuationEngine), each accepting a DuckDB connection and league context. Wire them into a new `intelligence/` router. Store computed outputs in new DuckDB tables (team_scorecards, team_directions, player_values). All outputs are deterministic and re-runnable — recomputing replaces the previous result.

---

## Standard Stack

### Core (inherited from Phase 1 — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | Read Phase 1 tables; write Phase 2 output tables | Already locked; analytical SQL is the right tool for aggregate scoring |
| pydantic | 2.x | Domain models for all engine inputs/outputs | Established pattern from Phase 1; type safety across layers |
| fastapi | 0.115.x | New routers: `/scorecard`, `/direction`, `/player-value` | Established pattern from Phase 1 |
| polars | 1.x | Bulk stat aggregation before scoring | Already in stack; DuckDB + Polars are the standard pairing for analytical computation |

### Supporting (no new installs needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Unit tests for each engine class | Every engine function is unit-testable with a seeded in-memory DuckDB |
| pytest-asyncio | 0.23.x | Async router tests | Same as Phase 1 |

### New Additions for Phase 2

None required. The full computation stack is covered by what Phase 1 already installed. Do not add scikit-learn, numpy, or pandas — they are not needed for rule-based formula engines and would add unnecessary weight.

**Installation (verification only):**
```bash
pip install duckdb==1.5.0 polars pydantic fastapi pytest pytest-asyncio
# All already present from Phase 1
```

---

## Architecture Patterns

### Recommended Project Structure Extension

```
backend/src/fantasy/
├── intelligence/                    # NEW — Phase 2 engines
│   ├── __init__.py
│   ├── scorecard_engine.py          # TEAM-01: 9 sub-score computation
│   ├── direction_engine.py          # TEAM-02/03/04/05: rule-based classification
│   ├── valuation_engine.py          # PLAY-01/02/03/04: 12-component player values
│   ├── models.py                    # Pydantic domain models for Phase 2 outputs
│   └── constants.py                 # Age thresholds, weight matrices, direction configs
├── routers/
│   └── intelligence.py              # NEW — GET /scorecard, /direction, /player-value
└── db/
    └── models.py                    # EXTENDED — add Phase 2 output tables
```

### Phase 2 Output Tables (new Alembic migration)

```sql
-- team_scorecards: computed scorecard per team per run
CREATE TABLE IF NOT EXISTS team_scorecards (
    id              INTEGER PRIMARY KEY,
    league_id       VARCHAR NOT NULL,
    roster_id       INTEGER NOT NULL,
    computed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    win_now         FLOAT NOT NULL,          -- 0.0-1.0 normalized
    future_value    FLOAT NOT NULL,
    depth           FLOAT NOT NULL,
    pick_capital    FLOAT NOT NULL,
    flexibility     FLOAT NOT NULL,
    fragility       FLOAT NOT NULL,
    age_risk        FLOAT NOT NULL,
    liquidity       FLOAT NOT NULL,
    positional_insulation FLOAT NOT NULL,
    composite       FLOAT NOT NULL,          -- weighted sum of sub-scores
    computation_json VARCHAR,                -- full input snapshot for audit
    UNIQUE (league_id, roster_id)
);

-- team_directions: direction label + confidence + alternates
CREATE TABLE IF NOT EXISTS team_directions (
    id              INTEGER PRIMARY KEY,
    league_id       VARCHAR NOT NULL,
    roster_id       INTEGER NOT NULL,
    computed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    primary_label   VARCHAR NOT NULL,        -- one of 8 direction strings
    confidence      FLOAT NOT NULL,          -- 0.0-1.0
    reasoning       VARCHAR NOT NULL,        -- human-readable explanation
    alternates_json VARCHAR NOT NULL,        -- JSON array of {label, confidence, gap}
    delta_json      VARCHAR NOT NULL,        -- JSON: what would change the label
    approved_moves  VARCHAR NOT NULL,        -- JSON array of approved move types
    discouraged_moves VARCHAR NOT NULL,      -- JSON array of discouraged move types
    UNIQUE (league_id, roster_id)
);

-- player_values: 12 components + 5 lenses per player per league
CREATE TABLE IF NOT EXISTS player_values (
    id              INTEGER PRIMARY KEY,
    league_id       VARCHAR NOT NULL,
    roster_id       INTEGER NOT NULL,        -- owning team for team-fit/direction lens
    player_id       VARCHAR NOT NULL,
    computed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 12 raw component scores (0.0-1.0 each)
    comp_production FLOAT,
    comp_short_term FLOAT,
    comp_role_stability FLOAT,
    comp_age_curve  FLOAT,
    comp_insulation FLOAT,
    comp_market_liquidity FLOAT,
    comp_positional_scarcity FLOAT,
    comp_fragility  FLOAT,
    comp_ceiling    FLOAT,
    comp_floor      FLOAT,
    comp_rerollability FLOAT,
    comp_contract   FLOAT,
    -- 5 lens aggregates
    lens_production FLOAT,
    lens_market     FLOAT,
    lens_insulation FLOAT,
    lens_team_fit   FLOAT,
    lens_direction  FLOAT,
    UNIQUE (league_id, roster_id, player_id)
);
```

### Pattern 1: Engine Class Architecture (Service Layer)

**What:** Each engine is a pure-Python class that accepts a DuckDB connection and a league context Pydantic model. Engines are stateless between calls — all state is read from DuckDB on each compute call. Engines do not know about HTTP, FastAPI, or routers.

**When to use:** All computation. Routers call engines; engines do not call routers.

**Example:**
```python
# fantasy/intelligence/scorecard_engine.py
import duckdb
from fantasy.intelligence.models import TeamScorecard, ScorecardInputs

class ScorecardEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def compute(self, league_id: str, roster_id: int) -> TeamScorecard:
        inputs = self._gather_inputs(league_id, roster_id)
        return TeamScorecard(
            league_id=league_id,
            roster_id=roster_id,
            win_now=self._score_win_now(inputs),
            future_value=self._score_future_value(inputs),
            depth=self._score_depth(inputs),
            pick_capital=self._score_pick_capital(inputs),
            flexibility=self._score_flexibility(inputs),
            fragility=self._score_fragility(inputs),
            age_risk=self._score_age_risk(inputs),
            liquidity=self._score_liquidity(inputs),
            positional_insulation=self._score_positional_insulation(inputs),
        )

    def _gather_inputs(self, league_id: str, roster_id: int) -> ScorecardInputs:
        # DuckDB queries against Phase 1 tables
        ...
```

### Pattern 2: Rule-Based Direction Classification with Confidence

**What:** The DirectionEngine maps 9 scorecard sub-scores to a direction label via a decision rule table. Confidence is computed as the normalized distance between the winning label's score and the next-best label's score. Alternates are all labels above a viable threshold (e.g., 70% of the winner's score).

**When to use:** Direction classification is always rule-based. Never use ML here — there are fewer than 16 data points per league, training is impossible, and the outputs must be explainable.

**Design:**
```python
# fantasy/intelligence/constants.py

# Each direction label maps to a weight vector over sub-scores
# Weights are relative priorities — what makes this direction different
DIRECTION_WEIGHTS: dict[str, dict[str, float]] = {
    "true_contender": {
        "win_now": 0.35, "depth": 0.20, "fragility": -0.20,  # fragility is a cost
        "future_value": 0.05, "pick_capital": 0.05,
        "flexibility": 0.10, "age_risk": -0.05, "liquidity": 0.00,
        "positional_insulation": 0.10
    },
    "fragile_contender": {
        "win_now": 0.30, "depth": 0.05, "fragility": 0.20,   # fragility is a signal
        "future_value": 0.00, "pick_capital": 0.05,
        "flexibility": 0.10, "age_risk": -0.15, "liquidity": -0.05,
        "positional_insulation": 0.00
    },
    "hard_rebuild": {
        "win_now": -0.30, "future_value": 0.35, "pick_capital": 0.25,
        "depth": 0.10, "fragility": 0.00, "flexibility": 0.10,
        "age_risk": 0.10, "liquidity": 0.05, "positional_insulation": 0.00
    },
    # ... 5 more direction labels
}

# Move types approved/discouraged by direction
DIRECTION_MOVE_MATRIX: dict[str, dict[str, list[str]]] = {
    "true_contender": {
        "approved": ["sell_future_picks", "buy_aging_producers", "buy_depth", "waiver_streamers"],
        "discouraged": ["sell_proven_starters", "start_youth_at_position_of_need", "hoard_picks"]
    },
    "hard_rebuild": {
        "approved": ["sell_aging_producers", "buy_rookie_picks", "sell_win_now_pieces", "hoard_youth"],
        "discouraged": ["buy_expiring_value", "extend_aging_RBs", "win_now_trades"]
    },
    # ... 6 more
}
```

```python
# fantasy/intelligence/direction_engine.py
from fantasy.intelligence.models import TeamScorecard, DirectionResult
from fantasy.intelligence.constants import DIRECTION_WEIGHTS, DIRECTION_MOVE_MATRIX

class DirectionEngine:
    def classify(self, scorecard: TeamScorecard) -> DirectionResult:
        scores = scorecard.as_dict()  # {"win_now": 0.7, "future_value": 0.3, ...}

        label_scores: dict[str, float] = {}
        for label, weights in DIRECTION_WEIGHTS.items():
            label_scores[label] = sum(
                scores[dim] * weight for dim, weight in weights.items()
            )

        ranked = sorted(label_scores.items(), key=lambda x: x[1], reverse=True)
        primary_label, primary_score = ranked[0]

        # Confidence: gap between #1 and #2 relative to total range
        confidence = (primary_score - ranked[1][1]) / (max(label_scores.values()) - min(label_scores.values()) + 1e-9)
        confidence = min(1.0, max(0.0, confidence))

        # Alternates: labels within 85% of winning score
        threshold = primary_score * 0.85
        alternates = [
            {"label": label, "score": score, "gap": round(primary_score - score, 3)}
            for label, score in ranked[1:]
            if score >= threshold
        ]

        # Delta: what sub-score change would flip the label
        delta = self._compute_delta(scores, ranked)

        return DirectionResult(
            primary_label=primary_label,
            confidence=round(confidence, 3),
            reasoning=self._build_reasoning(primary_label, scores, primary_score),
            alternates=alternates,
            delta=delta,
            approved_moves=DIRECTION_MOVE_MATRIX[primary_label]["approved"],
            discouraged_moves=DIRECTION_MOVE_MATRIX[primary_label]["discouraged"],
        )
```

### Pattern 3: Sub-Score Computation from Phase 1 Tables

**What:** Each sub-score is computed from DuckDB queries against Phase 1 tables. Scores are normalized to 0.0–1.0 using min-max normalization within the league context (relative to other teams in the same league).

**Critical design decision:** Sub-scores must be **league-relative**, not absolute. A "win-now" score of 0.8 means this team is near the top of the league in win-now potential — not that they have 80% of some absolute max. This ensures scores are meaningful for the direction engine comparisons.

**Sub-score computation sources:**

| Sub-score | Primary Input | DuckDB Tables | Computation Logic |
|-----------|--------------|---------------|-------------------|
| win-now | Current starter quality × fantasy points last season | `rosters`, `player_stats_weekly`, `players` | Weighted avg ADP-adjusted fantasy points of starters; normalize within league |
| future_value | Roster age profile weighted by position | `rosters`, `players` | Youth-weighted score: more value for players under positional peak age |
| depth | Bench quality relative to starters | `rosters`, `player_stats_weekly` | Bench-starter quality gap; how replaceable are starters |
| pick_capital | Number and quality of future picks | `traded_picks` | Round-weighted pick count (R1=3pts, R2=2pts, R3=1pt); years of picks held |
| flexibility | Roster composition breadth across positions | `rosters`, `players` | Positional spread + trade asset diversity; no single-position overconcentration |
| fragility | Concentration of production in few players | `rosters`, `player_stats_weekly` | Herfindahl-Hirschman Index of fantasy point concentration; injury history proxy |
| age_risk | Proportion of roster above positional peak age | `rosters`, `players` | Weighted count of players beyond positional peak age; position-specific thresholds |
| liquidity | How tradeable the roster assets are | `player_adp_baseline`, `transactions` | Trade velocity of owned players (appearances in recent trades in this league) |
| positional_insulation | Depth at each required lineup position | `rosters`, `players`, `leagues` | For each starting slot, does the bench have a +1 quality backup? |

### Pattern 4: Player Valuation — 12 Components + 5 Lenses

**What:** The ValuationEngine computes 12 raw component scores (0.0–1.0 each) per player, then aggregates them into 5 lenses based on which components are most relevant to each lens.

**Component → Lens mapping:**

| Lens | Components Included | Weighting Principle |
|------|--------------------|--------------------|
| production | current_production, short_term_utility, ceiling, floor_stability | Equal weight — raw output |
| market | market_liquidity, positional_scarcity, rerollability | Trade market perspective |
| insulation | insulation_value, role_stability, fragility (inverted), contract_security | How safe is this asset |
| team_fit | positional_scarcity (league-specific), role_stability | Does this team need this player specifically |
| direction_specific | All 12, reweighted by active direction weight vector | Context-adjusted value |

**Format adjustments (PLAY-02):**
```python
# fantasy/intelligence/constants.py

FORMAT_MULTIPLIERS = {
    # PPR value adjustment per position
    "ppr_1.0": {"WR": 1.15, "TE": 1.10, "RB": 1.10, "QB": 1.0},
    "ppr_0.5": {"WR": 1.07, "TE": 1.05, "RB": 1.05, "QB": 1.0},
    "ppr_0.0": {"WR": 1.0,  "TE": 1.0,  "RB": 1.0,  "QB": 1.0},
    # Superflex premium on QB
    "superflex": {"QB": 1.35},
    # TEP premium on TE
    "tep": {"TE": 1.15},
}
```

**Direction adjustments (PLAY-03):**
```python
# Direction-specific component weight overrides
DIRECTION_VALUE_WEIGHTS: dict[str, dict[str, float]] = {
    "true_contender": {
        "current_production": 0.30, "short_term_utility": 0.20,
        "age_curve": -0.05,   # deprioritize: age matters less now
        "ceiling": 0.15, "floor_stability": 0.15,
        "market_liquidity": 0.05, "insulation_value": 0.10,
        "role_stability": 0.05, "positional_scarcity": 0.05,
        "fragility": -0.10, "rerollability": -0.05, "contract_security": 0.05,
    },
    "hard_rebuild": {
        "current_production": 0.05, "short_term_utility": 0.00,
        "age_curve": 0.30,    # heavily prioritize: future value
        "ceiling": 0.25, "floor_stability": -0.05,
        "market_liquidity": 0.15, "insulation_value": 0.10,
        "role_stability": 0.05, "positional_scarcity": 0.05,
        "fragility": 0.00, "rerollability": 0.05, "contract_security": 0.00,
    },
    # ... 6 more directions
}
```

### Pattern 5: Age Curve Constants (verified from domain research)

These are the positional age thresholds used by the `age_curve` and `age_risk` components. Sourced from ESPN age curve analysis (2023, 37.9M data points) and multiple dynasty community sources.

```python
# fantasy/intelligence/constants.py

# Age at which production risk begins materially (players AT this age are at-risk)
POSITIONAL_PEAK_AGE = {
    "RB": 26,    # 90%+ of 250+ PPR seasons happen before 29; peak is 23-26; cliff starts at 28
    "WR": 28,    # Peak at Year 5 (≈age 25-26); sustained through age 30 for elite; cliff at 30+
    "TE": 30,    # "30 is far less of a cliff for TE"; breakout Year 2; sustained through Year 7
    "QB": 32,    # 67% of QB1 seasons ages 25-30; rushing cliff starts 27-29; passing sustains
}

# Age beyond which we assign maximum age_risk penalty
POSITIONAL_CLIFF_AGE = {
    "RB": 29,    # Sharp 25.2% decline from 28→29; only 8.4% of touches at 29+
    "WR": 31,
    "TE": 33,
    "QB": 35,
}

# Age curve scoring: players younger than PEAK_AGE get upside credit
# Players between PEAK and CLIFF get neutral-to-minor risk
# Players at or above CLIFF get maximum age risk
```

### Pattern 6: Move Recommendation Engine (TEAM-05)

**What:** The move recommendation engine is a lookup + ranking, not a search algorithm. Given a direction label and a scorecard, it selects move types from the approved list and ranks them by which sub-score gap is largest.

```python
# fantasy/intelligence/direction_engine.py (continued)

MOVE_TYPE_TARGETS: dict[str, str] = {
    # move_type → which sub-score gap it addresses
    "sell_aging_producers": "age_risk",
    "buy_rookie_picks": "pick_capital",
    "buy_depth": "depth",
    "sell_future_picks": "pick_capital",
    "buy_aging_producers": "win_now",
    "hoard_picks": "future_value",
    "sell_proven_starters": "liquidity",
    # ...
}

def rank_moves(self, direction_label: str, scorecard: TeamScorecard) -> list[str]:
    approved = DIRECTION_MOVE_MATRIX[direction_label]["approved"]
    # Sort by the size of the gap in the sub-score this move addresses
    scores = scorecard.as_dict()
    ranked = sorted(
        approved,
        key=lambda m: scores.get(MOVE_TYPE_TARGETS.get(m, ""), 0.5),
        reverse=True   # biggest gap = most urgent
    )
    return ranked
```

### Anti-Patterns to Avoid

- **Using ML for direction classification:** With 8-16 teams per league, training a classifier produces noise, not signal. Rule-based classification with explicit weight vectors is the correct approach — it produces explainable reasoning strings and deterministic alternates.
- **Absolute scoring instead of league-relative normalization:** A player's "win-now" contribution is only meaningful relative to their leaguemates. Normalize all sub-scores within the league context (min-max across all teams in the league). A league of all-contenders needs different scaling than a league of all rebuilders.
- **Recomputing player values on every API request:** Player valuation is expensive (12 components × N players per roster). Persist results to `player_values` table on a compute run; API reads from the table. Mark stale with `computed_at`.
- **Mixing engine logic into routers:** Engines must be testable without a running FastAPI server. Routers call engines; engines never import from routers.
- **Computing scorecards without handling missing stats:** Not all players have `player_stats_weekly` rows (rookies, late-season callups, new signings). Every sub-score formula must have an explicit default for missing player data — do not propagate NaN.
- **Ignoring the corrections table:** Phase 1's override system allows user corrections to any ingested value. The scorecard engine must apply the `corrections` table before computing sub-scores — corrected values take precedence over raw ingested values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Min-max normalization | Custom normalization function | Python inline formula with explicit bounds | It's 3 lines; but document the bounds clearly — per-league not global |
| JSON serialization of engine outputs to DuckDB | Custom serializer | `json.dumps()` consistent with Phase 1's `_dumps()` helper | Already established pattern in `league_repo.py` |
| Direction weight optimization | Manual weight tuning loop | Explicit `DIRECTION_WEIGHTS` constants dict + test-driven calibration | With 8-16 teams per league, no statistical method can tune these — use expert judgment + unit tests |
| Age curve data | Scraping external sites | Hardcoded constants in `constants.py` backed by research sources | The age thresholds are stable, well-researched, and don't change season-to-season. Maintain as named constants with source comments. |
| ADP proxy for market value | Build a scraper | Use `player_adp_baseline` table seeded in Phase 1 | Already ingested; Phase 2 consumes it. If baseline is stale/empty, surface as a named gap — don't silently skip. |

**Key insight:** Phase 2 is formula engineering, not machine learning. Every computation is a deterministic function of input data. The complexity is in defining sensible weights, thresholds, and normalization — not in training models.

---

## Common Pitfalls

### Pitfall 1: JSON Column Parsing — Phase 1 Stores Lists/Dicts as Strings

**What goes wrong:** `rosters.starters` is stored as a JSON string `'["4017","4663"]'`, not a native array. Querying it with DuckDB SQL without parsing causes string comparison failures.
**Why it happens:** Phase 1's `_dumps()` serializes all list/dict fields as VARCHAR. DuckDB does not auto-parse these.
**How to avoid:** In engine queries, parse JSON columns explicitly: `json_extract(starters, '$[*]')` in DuckDB SQL, or deserialize in Python with `json.loads()` before processing. Alternatively, use DuckDB's `from_json()` function.
**Warning signs:** Roster queries returning wrong player counts; picks queries finding no rows when picks exist.

### Pitfall 2: Scoring with Missing `player_stats_weekly` Rows

**What goes wrong:** New players (rookies, late additions, recently traded), players on IR all season, or players added after nfl_data_py's data window have zero rows in `player_stats_weekly`. Computing averages over these returns NULL or 0 — which tanks their sub-score unfairly.
**Why it happens:** The stat table is keyed on `(player_id, season, week)`. Players with no games produce no rows.
**How to avoid:** Use `COALESCE(stat_value, baseline_from_adp)` fallback. For players with no stats: use ADP rank as a proxy for production component if available; otherwise default to league median for their position. Document the fallback explicitly in the engine.
**Warning signs:** All rookies scoring 0.0 on every component; new roster additions appearing at bottom of all value lenses regardless of ADP.

### Pitfall 3: Direction Label Ties or Near-Ties

**What goes wrong:** Two direction labels score within 0.01 of each other. The primary label assignment is arbitrary and the confidence score is near-zero. The reasoning string is misleading because both directions are equally valid.
**Why it happens:** Weight vectors for similar labels (e.g., "retool" vs. "fringe playoff") can overlap significantly.
**How to avoid:** When confidence < 0.10, always produce at least two alternates in the result (guaranteed by TEAM-03). Add a minimum confidence floor to the reasoning string: "Low confidence — team is on the border of [label A] and [label B]." Do not hide this from the user.
**Warning signs:** All teams in the league getting the same direction label; confidence always near 0.

### Pitfall 4: League-Relative vs. Cross-League Normalization

**What goes wrong:** Sub-scores are normalized across all leagues combined, not within a single league. This causes a mediocre team in a stacked league to score the same as a strong team in a weak league.
**Why it happens:** DuckDB queries that pull all teams without a `league_id` filter.
**How to avoid:** Every normalization query MUST include a `WHERE league_id = ?` filter before computing min/max for normalization bounds. This is not optional — it is part of the league-relative design contract.
**Warning signs:** Teams from different leagues appearing in the same normalization range.

### Pitfall 5: Pick Capital Counting Picks That Don't Exist

**What goes wrong:** The `traded_picks` table only contains picks that have been traded away from their original owner. Picks that have NOT been traded are NOT in the table — they belong to their original owner by default (Sleeper's convention).
**Why it happens:** Phase 1's `traded_picks` table mirrors Sleeper's `traded_picks` endpoint, which only tracks traded picks. "Untouched" picks are implied by roster_id.
**How to avoid:** Pick capital computation requires TWO queries: (1) picks from `traded_picks` where `owner_id = this_roster_id` (traded picks now owned by this team), PLUS (2) original picks for future seasons where this team's roster has NOT traded them away. The second query requires checking which seasons exist in `traded_picks` for this roster and which do NOT.
**Warning signs:** Pick capital scores are zero for teams with known untouched picks; pick capital dramatically underestimates for non-trading teams.

### Pitfall 6: Direction Engine Not Re-Running After Scorecard Changes

**What goes wrong:** User triggers a scorecard recompute (e.g., after a manual correction), but the direction label is stale because DirectionEngine reads from the `team_directions` table, not from the live ScorecardEngine output.
**Why it happens:** If engines are wired sequentially but independently, a scorecard recompute does not automatically trigger a direction recompute.
**How to avoid:** The intelligence compute pipeline must be: ScorecardEngine → DirectionEngine → ValuationEngine, in that sequence. Any recompute at step N must cascade through steps N+1 and N+2. Implement this as a single orchestrated `IntelligenceService.compute_all(league_id)` method.
**Warning signs:** Direction label reflects old scorecard; direction-weighted player values don't match current direction.

---

## Code Examples

Verified patterns from official sources and Phase 1 codebase:

### DuckDB JSON Column Parsing (Phase 1 compatibility)
```python
# Source: DuckDB docs + Phase 1 pattern discovery
# rosters.starters is stored as JSON string '["4017","4663"]'
# Parse in Python after fetching:
import json
rows = conn.execute(
    "SELECT roster_id, starters, reserve, taxi FROM rosters WHERE league_id = ?",
    [league_id]
).fetchall()
for row in rows:
    roster_id = row[0]
    starters: list[str] = json.loads(row[1])  # critical: json.loads not eval
    ir: list[str] = json.loads(row[2]) if row[2] else []
    taxi: list[str] = json.loads(row[3]) if row[3] else []
```

### DuckDB + Polars for Bulk Stat Aggregation
```python
# Source: https://duckdb.org/docs/stable/guides/python/polars
import duckdb
import polars as pl

def get_player_season_stats(conn: duckdb.DuckDBPyConnection, player_ids: list[str], season: int) -> pl.DataFrame:
    """Aggregate weekly stats into season totals for a set of players."""
    result = conn.execute("""
        SELECT
            player_id,
            SUM(fantasy_points)      AS season_fantasy_pts,
            COUNT(week)              AS games_played,
            AVG(fantasy_points)      AS ppg,
            SUM(receiving_yards)     AS rec_yards,
            SUM(rushing_yards)       AS rush_yards,
            SUM(passing_yards)       AS pass_yards
        FROM player_stats_weekly
        WHERE player_id IN (SELECT unnest(?))
          AND season = ?
        GROUP BY player_id
    """, [player_ids, season]).pl()  # .pl() returns Polars DataFrame directly
    return result
```

### Min-Max Normalization Within League
```python
# Pattern: always normalize within league context
def normalize_within_league(
    values: dict[int, float]  # roster_id -> raw score
) -> dict[int, float]:
    """Normalize raw scores to 0.0-1.0 relative to league min/max."""
    if not values:
        return {}
    min_val = min(values.values())
    max_val = max(values.values())
    span = max_val - min_val
    if span < 1e-9:
        return {k: 0.5 for k in values}  # all teams equal → middle score
    return {k: (v - min_val) / span for k, v in values.items()}
```

### Pick Capital Computation (both owned traded picks + untouched original picks)
```python
# Phase 2 must count BOTH types of picks
ROUND_WEIGHTS = {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}

def compute_pick_capital(conn: duckdb.DuckDBPyConnection, league_id: str, roster_id: int, current_season: int) -> float:
    """Count pick capital: traded picks now owned + untouched original picks."""
    # Traded picks where this team is now the owner
    traded = conn.execute("""
        SELECT season, round FROM traded_picks
        WHERE league_id = ? AND owner_id = CAST(? AS VARCHAR)
          AND CAST(season AS INTEGER) >= ?
    """, [league_id, roster_id, current_season]).fetchall()

    # Seasons where this team's pick HAS been traded away (no longer owns original)
    traded_away_seasons = conn.execute("""
        SELECT DISTINCT season, round FROM traded_picks
        WHERE league_id = ? AND roster_id = ?
          AND CAST(season AS INTEGER) >= ?
    """, [league_id, roster_id, current_season]).fetchall()
    traded_away_set = {(r[0], r[1]) for r in traded_away_seasons}

    # Original picks not traded away (future seasons × rounds)
    future_seasons = [str(current_season + i) for i in range(3)]  # next 3 years
    original_rounds = [1, 2, 3]  # standard dynasty pick rounds
    untouched = [
        (season, rnd) for season in future_seasons for rnd in original_rounds
        if (season, rnd) not in traded_away_set
    ]

    all_picks = traded + untouched
    return sum(ROUND_WEIGHTS.get(rnd, 0.5) for _, rnd in all_picks)
```

### Confidence Score Computation for Direction Label
```python
# Pattern: confidence = normalized gap between #1 and #2 label scores
def compute_confidence(label_scores: dict[str, float]) -> float:
    if len(label_scores) < 2:
        return 1.0
    sorted_scores = sorted(label_scores.values(), reverse=True)
    top, second = sorted_scores[0], sorted_scores[1]
    score_range = sorted_scores[0] - sorted_scores[-1]
    if score_range < 1e-9:
        return 0.0   # all labels score equally — no confidence
    gap = top - second
    return min(1.0, gap / score_range)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ML classification for team archetypes | Rule-based weighted scoring with explicit constants | Community convergence 2022-2024 | Explainable outputs; no training data required; weights inspectable |
| Global ADP for player values | League-specific format adjustments on top of ADP baseline | Industry standard 2023+ | PPR/superflex/TEP multipliers change relative positional value materially |
| Single dynasty value per player | Multi-lens decomposition (production, market, insulation, team-fit, direction) | Emerging 2024+ (KTC liquidity score, Dynasty Toolbox contend/rebuild split) | Same player has meaningfully different value depending on team context |
| Win% only for team quality | Composite scorecard with 9 sub-dimensions | GSD-specific design based on domain research | Captures that a 6-6 team can be a future powerhouse or a time bomb |

**Deprecated/outdated:**
- Single "team grade" with no decomposition: does not tell the user what to do. This system must never expose a single opaque number — every sub-score is displayed as TEAM-01 requires.
- "Points For" as a proxy for team quality alone: a high-scoring team with all RBs aged 28+ is in terminal decline. Age risk must be a separate dimension.

---

## Open Questions

1. **Direction weight vector calibration**
   - What we know: The 8 direction labels and their general meaning are defined in the requirements. Weight vectors in Pattern 2 are a starting hypothesis derived from domain research.
   - What's unclear: Whether the proposed weights will produce intuitive, non-degenerate classifications against real league data. Two similar labels (e.g., "retool" vs. "productive struggle") may need carefully differentiated weights to avoid always scoring together.
   - Recommendation: Phase 2 Wave 0 should include a calibration notebook or script that runs the direction engine against synthetic roster snapshots and prints the ranked label outputs. Validate manually before wire-in to the API. This is a required human checkpoint — not an automated test.

2. **ADP Baseline Coverage**
   - What we know: `player_adp_baseline` is seeded in Phase 1 from a CSV. As of the handoff notes, the real ADP CSV file was not validated against production data.
   - What's unclear: How many players in active league rosters are missing from the ADP baseline. If a significant fraction of players have no ADP entry, the production component fallback chain is critical.
   - Recommendation: Phase 2 Wave 0 should query `SELECT COUNT(*) FROM players p LEFT JOIN player_adp_baseline b ON p.player_id = b.player_id WHERE b.player_id IS NULL AND p.position IN ('QB','RB','WR','TE')` to measure baseline coverage before building valuation logic.

3. **"Untouched" Pick Counting Approach**
   - What we know: The `traded_picks` table only contains picks that have changed hands. Pitfall 5 documents the dual-query approach.
   - What's unclear: The exact number of future seasons and rounds Sleeper tracks in its `traded_picks` endpoint. If Sleeper only returns picks out 2 years, the "untouched picks" calculation needs to know the boundary.
   - Recommendation: At implementation time, query a real league's `traded_picks` to find the max season year returned. Use that as the lookahead window for untouched pick calculation.

4. **Fragility / Injury Risk Proxy**
   - What we know: The requirements specify fragility as a sub-score. Injury history is not directly in the Phase 1 tables — `player_stats_weekly` shows games played but not injury designations.
   - What's unclear: Whether "games played" (as a fraction of possible games) is a sufficient proxy for fragility, or whether we need to surface this as LOW confidence or flag it as a data gap.
   - Recommendation: Use `games_played / max_possible_games` as the fragility proxy. This is computable from `player_stats_weekly`. Flag in the scorecard output that fragility is based on availability, not diagnosed injury risk. That limitation is acceptable for Phase 2.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `backend/pyproject.toml` — already exists from Phase 1 |
| Quick run command | `pytest backend/tests/ -x -q -k "not integration"` |
| Full suite command | `pytest backend/tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEAM-01 | 9 sub-scores all produced, none NULL | unit | `pytest backend/tests/test_scorecard_engine.py::test_all_subscores_present -x` | Wave 0 |
| TEAM-01 | Sub-scores normalized 0.0-1.0 | unit | `pytest backend/tests/test_scorecard_engine.py::test_subscores_in_range -x` | Wave 0 |
| TEAM-01 | Pick capital counts both traded and untouched picks | unit | `pytest backend/tests/test_scorecard_engine.py::test_pick_capital_dual_source -x` | Wave 0 |
| TEAM-02 | Direction label is one of 8 valid strings | unit | `pytest backend/tests/test_direction_engine.py::test_valid_label -x` | Wave 0 |
| TEAM-02 | High win-now + low future-value team → contender-side label | unit | `pytest backend/tests/test_direction_engine.py::test_contender_signal -x` | Wave 0 |
| TEAM-02 | High future-value + low win-now team → rebuild-side label | unit | `pytest backend/tests/test_direction_engine.py::test_rebuild_signal -x` | Wave 0 |
| TEAM-03 | Confidence score 0.0-1.0 always produced | unit | `pytest backend/tests/test_direction_engine.py::test_confidence_range -x` | Wave 0 |
| TEAM-03 | At least 2 alternates always in result (or all 7 others if below threshold) | unit | `pytest backend/tests/test_direction_engine.py::test_minimum_alternates -x` | Wave 0 |
| TEAM-03 | Delta output describes which sub-score change flips the label | unit | `pytest backend/tests/test_direction_engine.py::test_delta_present -x` | Wave 0 |
| TEAM-04 | Approved and discouraged move lists non-empty for all 8 labels | unit | `pytest backend/tests/test_direction_engine.py::test_move_matrix_completeness -x` | Wave 0 |
| TEAM-05 | Ranked move list length ≥ 1 and contains only approved move types | unit | `pytest backend/tests/test_direction_engine.py::test_ranked_moves -x` | Wave 0 |
| PLAY-01 | 12 component scores all produced per player | unit | `pytest backend/tests/test_valuation_engine.py::test_all_components_present -x` | Wave 0 |
| PLAY-01 | Player with no stats → defaults applied, no NaN | unit | `pytest backend/tests/test_valuation_engine.py::test_missing_stats_defaults -x` | Wave 0 |
| PLAY-02 | PPR=1.0 produces higher WR/TE value than PPR=0.0 for same player | unit | `pytest backend/tests/test_valuation_engine.py::test_ppr_format_adjustment -x` | Wave 0 |
| PLAY-02 | Superflex=True produces higher QB value than superflex=False | unit | `pytest backend/tests/test_valuation_engine.py::test_superflex_adjustment -x` | Wave 0 |
| PLAY-03 | Same player scores higher on direction_specific lens in hard_rebuild direction than true_contender direction (for young player) | unit | `pytest backend/tests/test_valuation_engine.py::test_direction_reweight -x` | Wave 0 |
| PLAY-04 | All 5 lenses produced per player response | unit | `pytest backend/tests/test_valuation_engine.py::test_five_lenses -x` | Wave 0 |
| All | Intelligence pipeline produces same result when run twice (deterministic) | integration | `pytest backend/tests/test_intelligence_service.py::test_idempotent_compute -x` | Wave 0 |
| All | API GET /scorecard/{league_id}/{roster_id} returns 200 with all 9 sub-scores | integration | `pytest backend/tests/test_intelligence_router.py::test_scorecard_endpoint -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/ -x -q -k "not integration"`
- **Per wave merge:** `pytest backend/tests/ -v --tb=short`
- **Phase gate:** Full suite green + human direction label review before Phase 3 begins (matches ROADMAP.md hard gate intent)

### Wave 0 Gaps

- [ ] `backend/tests/test_scorecard_engine.py` — covers TEAM-01; seeded in-memory DuckDB with Phase 1 table schema
- [ ] `backend/tests/test_direction_engine.py` — covers TEAM-02, TEAM-03, TEAM-04, TEAM-05; tests with synthetic scorecard inputs (no DB needed)
- [ ] `backend/tests/test_valuation_engine.py` — covers PLAY-01, PLAY-02, PLAY-03, PLAY-04; seeded player + stats data
- [ ] `backend/tests/test_intelligence_service.py` — integration; covers orchestrated compute pipeline idempotency
- [ ] `backend/tests/test_intelligence_router.py` — integration; FastAPI test client against real router
- [ ] `backend/src/fantasy/intelligence/__init__.py` — package marker
- [ ] `backend/src/fantasy/intelligence/constants.py` — all weight vectors, age thresholds, move matrices
- [ ] `backend/src/fantasy/intelligence/models.py` — Pydantic domain models for Phase 2 outputs
- [ ] Alembic migration: `004_phase2_output_tables.py` — creates `team_scorecards`, `team_directions`, `player_values`

*(Existing conftest.py from Phase 1 covers in-memory DuckDB fixture — extend it with Phase 2 table schema seeds.)*

---

## Sources

### Primary (HIGH confidence)
- Phase 1 codebase (`backend/src/fantasy/`) — confirmed data models, table schemas, repository patterns, established conventions
- Phase 1 RESEARCH.md — confirmed stack, DuckDB patterns, upsert idioms
- https://duckdb.org/docs/stable/guides/python/polars — DuckDB + Polars integration, `.pl()` method, lazy evaluation
- https://duckdb.org/docs/stable/clients/python/dbapi — DuckDB connection patterns (Phase 1 confirmed)

### Secondary (MEDIUM confidence)
- https://www.espn.com/fantasy/football/story/_/id/37933720/2023-fantasy-football-players-peak-decline-quarterback-running-back-wide-receiver — Position-specific age curves verified from ESPN analysis of 37.9M data points (2023)
- https://keeptradecut.com/frequently-asked-questions — KTC Liquidity Score methodology (crowdsourced trade frequency)
- Dynasty community research (Dynasty Toolbox, Draft Sharks, Fantasy Footballers) — win-now/rebuild spectrum, positional valuation philosophy; cross-validated across 3+ independent sources
- Python.org weighted scoring discussion — confidence scoring pattern
- https://camillovisini.com/coding/abstracting-fastapi-services — FastAPI service layer separation pattern

### Tertiary (LOW confidence — flag for validation)
- Direction label weight vectors (`DIRECTION_WEIGHTS` in constants.py) — starting hypothesis derived from domain research; requires calibration against real league data before production use. Validate via human review checkpoint.
- Specific sub-score formula constants (e.g., round weights for pick capital: R1=3, R2=2, R3=1) — derived from community convention; not backed by a single authoritative source. Adjust during calibration.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries from Phase 1; no new installs required; DuckDB + Polars + Pydantic verified
- Architecture: HIGH — engine/service pattern is established FastAPI community standard; Phase 1 already implements it correctly
- Scoring formulas: MEDIUM — computation logic is sound; specific weight constants are educated starting points requiring calibration
- Age curve constants: MEDIUM-HIGH — sourced from ESPN empirical research (37.9M data points, 2023); consistent with multiple community sources
- Pitfalls: HIGH — all 6 pitfalls either directly confirmed from Phase 1 code inspection (JSON column parsing, corrections table) or from well-documented domain gotchas

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stack is stable; dynasty age curve research does not change season-to-season)
