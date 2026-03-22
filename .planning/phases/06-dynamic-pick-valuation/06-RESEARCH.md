# Phase 6: Dynamic Pick Valuation - Research

**Researched:** 2026-03-21
**Domain:** Dynasty pick valuation algorithms, calendar timing cycles, manager demand signals, FastAPI engine patterns, DuckDB query patterns
**Confidence:** HIGH (architecture and stack — extends verified Phase 2/4/5 patterns), MEDIUM (formula constants — derived from dynasty community methodology, no single authoritative quantitative source), LOW (rebuilder-count demand adjustment weight — no published precedent; must be specified empirically)

---

## User Constraints

> Copied verbatim from 06-CONTEXT.md. Planner MUST honor these.

### Locked Decisions

**Class strength signal**
- D-01: Class strength is a neutral placeholder in Phase 6 — all draft classes treated as neutral until Phase 7 wires in actual class evaluation
- D-02: No ADP proxy used for class strength — Phase 7 owns class evaluation; Phase 6 must design the signal hook so Phase 7 can plug in without engine changes

**Display surface**
- D-03: No new picks page — Phase 6 is a pure engine upgrade
- D-04: Dynamic pick values surface wherever picks already appear: Phase 5 trade evaluator (replaces Phase 2 baseline), existing league views — no new routes or pages introduced

**Timing recommendations (PICK-03)**
- D-05: Three timing states: sell now / hold until rookie fever / use on the clock
- D-06: Each timing rec shows label + one-line reasoning tied to the inputs that drove it (e.g., "Team trending down, sell before rookie fever inflates competition")
- D-07: Timing recs surface inline where picks are displayed — not a separate section

**Manager demand signals (PICK-02)**
- D-08: Demand signals are fully derived — no manual override
- D-09: Two signal sources: (1) Phase 4 direction label (rebuilder = high demand, contender = low), (2) manager trade history premium pattern (consistent pick overpayer = elevated demand signal even if direction label is ambiguous)
- D-10: Both signals are combined into a single per-manager demand factor consumed by the pick valuation engine

### Claude's Discretion

- Exact formula for combining standings, draft proximity, rebuilder count, and demand signals into pick value
- Calendar timing decay curve (how value changes as rookie draft approaches)
- How to quantify "pick premium" from trade history (delta approach, frequency approach, or hybrid)
- How demand factor is normalized and weighted relative to other pick value inputs
- Specific Phase 7 hook interface for class strength injection

### Deferred Ideas (out of scope — do not plan)

- Actual class strength evaluation — Phase 7 (Rookie Board) owns this; Phase 6 provides the hook
- Roster-fit filtered pick value (which pick is best for this team vs. best in abstract) — Phase 7 (PICK-05)
- Draft room view (best pick vs. trading the pick) — Phase 7 (PICK-06)
- Historical pick value backtesting — Phase 8

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PICK-01 | System computes dynamic pick values adjusted for current standings, calendar timing (draft proximity), class strength perception, and active rebuilder count in this league | Four-factor formula documented in Architecture Patterns; standings-to-slot projection, calendar multiplier curve, class_strength hook, and rebuilder_factor all specified |
| PICK-02 | System adjusts pick values based on manager-specific demand signals within the league | Two-source demand factor documented: direction label + trade premium pattern; normalization approach specified |
| PICK-03 | System generates pick timing recommendations per pick: sell now / hold until rookie fever / use on the clock, with reasoning | Three-state decision tree documented with community-verified timing windows; one-line reasoning template per state |

---

## Summary

Phase 6 extends the established Phase 2/4/5 engine-class pattern to add a `picks/` package. The core output is a `PickEngine` that computes a dynamic pick value from four inputs: (1) standings-based expected draft slot, (2) calendar timing multiplier, (3) class strength signal (neutral float in Phase 6, typed hook for Phase 7), and (4) league-specific demand adjustment from rebuilder count and manager demand factors. A new `/picks` FastAPI router exposes this engine. Phase 5's pick value lookup is redirected from the Phase 2 baseline to this engine's output.

No new libraries are needed. No ML. No scraping of external pick value sources. The formula is deterministic and re-runnable — the same pattern as all prior phase engines.

The dynasty community has well-established methodology on three of the four inputs:
- **Standings → draft slot**: Expected draft position is computed from current win percentage against remaining opponents (Elo-like, but standings-only is sufficient for the tool's purpose). Community consensus is that the worst record gets the first pick; a logistic function on win rate maps teams to expected pick ranges.
- **Calendar timing**: There is strong community consensus on an annual pick value cycle — picks are lowest value in September–October (regular season, owners prioritize immediate help) and peak value in April–May (NFL Draft fever, owners will overpay to draft their target). This cycle is quantifiable as a multiplier against base pick value.
- **Class strength**: The community acknowledges this matters but there is no published quantitative standard. The placeholder float (0.0 = neutral) is the correct Phase 6 approach.
- **Rebuilder demand**: No published formula exists. The approach of counting active rebuilders in the league and applying a supply/demand adjustment is novel to this tool. Research found qualitative support (the Harstad contender/rebuilder framework confirms rebuilders bid up future picks) but no formula precedent — Claude's discretion is appropriate here.

---

## Standard Stack

### Core (inherited — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | Read picks, standings, manager_profiles tables; write pick_values output table | Already locked; analytical queries against existing Phase 1/2/4 tables |
| pydantic | 2.x | Domain models for pick engine inputs/outputs, Phase 7 hook interface | Established pattern across all phases |
| fastapi | 0.115.x | New `/picks` router following Phase 5 trade router pattern | Established pattern |
| polars | 1.x | Bulk aggregation if multiple picks computed in batch | Already in stack |

### Supporting (no new installs)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Unit tests for PickEngine formula components | Every formula subfunction is independently testable with seeded DuckDB |
| pytest-asyncio | 0.23.x | Async router integration tests | Same as all prior phases |

### Not Needed

Do not add `numpy`, `scipy`, or `pandas`. The formula is arithmetic — a handful of floats combined with weights. DuckDB handles all data retrieval. Polars handles any bulk aggregation. These libraries add no value and increase dependency weight.

**Version verification:**
All packages are already installed from prior phases. No new pip installs required.

---

## Dynasty Pick Valuation Algorithm — Research Synthesis

This section documents the community-verified methodology the Phase 6 engine should implement. Confidence levels are assigned per component.

### Component 1: Standings-Based Expected Draft Slot (CONFIDENCE: HIGH)

**Community consensus (multiple sources):** Dynasty rookie draft order follows inverse standings — worst record picks first. This is a near-universal rule in dynasty leagues.

**The computation challenge:** For in-season picks (owned by a team still playing), the draft slot is unknown. For off-season picks, the slot may be locked or projected. The engine must handle both states.

**Recommended approach:**

For current-year picks where the season is complete: use final standings rank directly.

For current-year picks mid-season or for future-year picks: compute an expected draft position (EDP) from the team's current win rate with a regression-to-mean adjustment for remaining games. Teams on losing streaks skew toward higher (worse) picks; teams on winning streaks skew toward lower (better) picks.

```python
# standings-to-slot projection
# win_pct: current W/(W+L), range 0.0-1.0
# remaining_games: int, games left in season
# league_size: number of teams
# returns: expected_slot float (1.0 = first pick, league_size = last pick)

def expected_draft_slot(win_pct: float, remaining_games: int, league_size: int) -> float:
    # Season-end win projection: current + regression toward 0.5 for remaining games
    # Weight current evidence by games_played, regress remaining toward 50%
    games_played = TOTAL_SEASON_GAMES - remaining_games
    regressed_win_pct = (
        (win_pct * games_played + 0.5 * remaining_games) / TOTAL_SEASON_GAMES
    )
    # Convert win_pct to rank percentile (lower win_pct = higher draft slot)
    # Rank is computed league-wide; this function returns the percentile
    # Actual slot = round(regressed_rank * league_size) clamped to [1, league_size]
    ...
```

**Pick value by slot**: Community data from DynastyProcess (verified HIGH confidence) shows a sharp non-linear curve:
- Slot 1.01: 83% hit rate
- Slots 1.02–1.04: 71% hit rate
- Slots 1.05–1.08: 38% hit rate (major drop)
- Second round: 22% hit rate
- Third round: 8% hit rate

This non-linearity means the slot-to-value curve should be exponential/power function, not linear. A simple power decay (value = base_value * (1/slot)^k) captures this correctly. Constant `k` of approximately 0.5–0.7 fits the published hit-rate data.

### Component 2: Calendar Timing Multiplier (CONFIDENCE: HIGH)

**Community consensus (multiple sources, verified):** Dynasty pick values follow a highly predictable annual cycle. This is the most robustly documented finding in dynasty pick trading literature.

**Published cycle (HIGH confidence from Footballguys, Fantasy Footballers, The Undroppables, DynastyProcess):**

| Calendar Period | Pick Value State | Multiplier Direction |
|-----------------|-----------------|---------------------|
| September–October | Season lowest — owners sell picks for immediate help | Buy window (multiplier: ~0.85–0.90x of theoretical) |
| November–December | Rising as playoff pushers trade picks for veterans | Rising |
| January–February | Post-season, rising with early draft speculation | Rising |
| March–April | NFL Draft: rapid appreciation as class crystallizes | Peak approach |
| April (NFL Draft week) | Peak "rookie fever" — managers will overpay | Peak (multiplier: ~1.15–1.20x of theoretical) |
| May–June | Rookie draft executed, hype deflates | Declining |
| July–August | Lowest offseason point for future picks | Near-season low |

**Recommended implementation:** A piecewise linear multiplier keyed to `calendar_month` (1–12). This is more maintainable than a sigmoid and easier to tune. Constants live in `picks/constants.py` as `CALENDAR_TIMING_MULTIPLIERS: dict[int, float]`.

The timing multiplier applies on top of the base slot value. It is not a separate dimension — it is part of the pick's computed value.

**Timing recommendation logic** derives directly from the timing multiplier:
- Multiplier trending to peak (February–April): `hold until rookie fever` — value still rising
- Multiplier at or near peak (April): `sell now` if the team's standing trajectory is also worsening (pick may slip)
- Pick already drafted (on the clock, draft underway): `use on the clock`
- Mid-season with pick holder trending toward worse record: `sell now` — pick will appreciate in position AND calendar is unfavorable

### Component 3: Class Strength Signal (CONFIDENCE: HIGH — design decision, not research finding)

**Decision D-01/D-02 are locked:** neutral placeholder `class_strength: float = 0.0` in Phase 6.

**Phase 7 hook design (Claude's discretion per context):**

The class strength parameter must be a named, typed Pydantic field so Phase 7 can inject a real value without touching Phase 6 engine code. The injection point is the `PickValuationContext` model.

```python
# picks/models.py
class PickValuationContext(BaseModel):
    pick: TradedPick
    league_id: str
    # Phase 7 injects here — Phase 6 always passes 0.0
    class_strength_signal: float = Field(
        default=0.0,
        description="Class strength deviation from neutral. Injected by Phase 7. "
                    "Range: -1.0 (historically weak class) to +1.0 (historically strong). "
                    "Phase 6 hardcodes 0.0 (neutral).",
        ge=-1.0,
        le=1.0,
    )
```

The class strength signal applies as an additive offset to the base slot value: `adjusted_value = base_value * (1 + CLASS_STRENGTH_WEIGHT * class_strength_signal)`. Constant `CLASS_STRENGTH_WEIGHT` lives in `constants.py` for easy Phase 7 tuning.

### Component 4: Demand Adjustment (CONFIDENCE: MEDIUM)

#### 4a. Rebuilder Count in League

**Community support (qualitative, MEDIUM confidence):** The Harstad contender/rebuilder framework explicitly states that "in leagues with multiple rebuilders, younger assets command premium pricing since demand concentrates among teams seeking future production." No published formula exists for this.

**Recommended approach:** Count teams whose Phase 4 direction label is one of: `hard_rebuild`, `elite_value_accumulation`, `one_year_punt`. Express as a ratio: `rebuilder_ratio = rebuilder_count / league_size`. Apply as a multiplier offset against base pick value.

```python
# Rebuilder demand adjustment
# rebuilder_ratio: float [0.0, 1.0]
# NEUTRAL_REBUILDER_RATIO: float = 0.25  # ~3 of 12 teams — normal baseline
# MAX_REBUILDER_PREMIUM: float = 0.15    # maximum ±15% adjustment

rebuilder_delta = rebuilder_ratio - NEUTRAL_REBUILDER_RATIO
rebuilder_adjustment = rebuilder_delta * MAX_REBUILDER_PREMIUM / (1 - NEUTRAL_REBUILDER_RATIO)
```

This produces zero adjustment at the baseline ratio, positive adjustment when more teams are rebuilding (higher demand for picks), negative when fewer are rebuilding (lower demand). Constants are named and live in `picks/constants.py`.

#### 4b. Per-Manager Demand Factor

**From D-09:** Two signal sources combined into one `demand_factor: float` per manager.

**Signal 1: Direction label**
Map Phase 4 `primary_label` to a demand score:
- `hard_rebuild` → 1.0
- `elite_value_accumulation` → 0.9
- `one_year_punt` → 0.8
- `retool` → 0.6
- `productive_struggle` → 0.5
- `fringe_playoff` → 0.4
- `fragile_contender` → 0.2
- `true_contender` → 0.1

**Signal 2: Trade history pick premium pattern**
From Phase 4 `manager_profiles`, the `archetype_specific_overpayer` classification for picks is the most direct signal. Recommended: frequency-based approach over delta-based.

Delta approach problem: KTC/ADP values at trade time are unavailable for historical trades in Phase 1 ingestion. Computing "how much extra they paid" requires external value data that doesn't exist in the system.

Frequency approach: count trades where the manager received picks (as a fraction of total trades). A manager who receives picks in >60% of trades is a pick demander. This is computable entirely from the Phase 1 `trades` table.

```python
# Pick demand frequency signal
pick_reception_rate = trades_where_manager_received_pick / total_trades
# Normalize to [0.0, 1.0] using sigmoid centered at 0.4
# Below 0.4 reception rate: low demand signal
# Above 0.4: elevated demand signal
demand_from_history = sigmoid(k=8, center=0.4, x=pick_reception_rate)
```

**Combining the two signals:**
```python
# D-10: combine direction label score + history signal
demand_factor = (DIRECTION_DEMAND_WEIGHT * direction_demand_score
                 + HISTORY_DEMAND_WEIGHT * demand_from_history)
# Constants: DIRECTION_DEMAND_WEIGHT = 0.6, HISTORY_DEMAND_WEIGHT = 0.4
# (Direction label is more stable signal; history is noisy with low trade counts)
```

**Evidence floor:** Apply the same `MIN_TRADE_EVIDENCE_THRESHOLD = 10` constant from Phase 4. Below 10 trades, `demand_from_history` is suppressed (weighted to zero) and only the direction label signal is used. This must be a named constant in `picks/constants.py`, not a magic number.

### Full Pick Value Formula

```python
def compute_pick_value(
    context: PickValuationContext,
    standings_data: TeamStandingsRow,
    league_context: LeaguePickContext,
) -> PickValue:
    # Step 1: Slot-based value from standings projection
    slot = expected_draft_slot(
        win_pct=standings_data.win_pct,
        remaining_games=standings_data.remaining_games,
        league_size=league_context.league_size,
    )
    base_value = slot_to_base_value(slot, league_context.league_size)  # power decay

    # Step 2: Apply calendar timing multiplier
    calendar_mult = CALENDAR_TIMING_MULTIPLIERS[current_month]
    timed_value = base_value * calendar_mult

    # Step 3: Apply class strength signal (Phase 7 hook — neutral in Phase 6)
    class_adjusted = timed_value * (
        1 + CLASS_STRENGTH_WEIGHT * context.class_strength_signal
    )

    # Step 4: Apply league-level rebuilder count adjustment
    rebuilder_adj = compute_rebuilder_adjustment(league_context.rebuilder_ratio)
    league_adjusted = class_adjusted * (1 + rebuilder_adj)

    # Step 5: Apply per-manager demand factor (for demand-adjusted value)
    # Note: base value is per-pick; demand factor is per buyer/seller pairing
    # demand_adjusted_value is the effective value when trading TO a high-demand manager
    demand_factor = context.target_manager_demand_factor  # pre-computed, 0.0-1.0
    demand_premium = DEMAND_FACTOR_MAX_PREMIUM * (demand_factor - 0.5) * 2
    demand_adjusted_value = league_adjusted * (1 + demand_premium)

    return PickValue(
        pick=context.pick,
        base_value=base_value,
        timed_value=timed_value,
        league_adjusted_value=league_adjusted,
        demand_adjusted_value=demand_adjusted_value,
        timing_recommendation=compute_timing_rec(slot, standings_data, current_month),
        timing_reasoning=compute_timing_reasoning(slot, standings_data, current_month),
        computed_at=datetime.utcnow(),
    )
```

### Timing Recommendation Decision Tree

```python
def compute_timing_rec(
    slot: float,
    standings: TeamStandingsRow,
    month: int,
) -> TimingLabel:
    # State 1: On the clock (draft in progress or imminent — Phase 7 context)
    if standings.draft_in_progress:
        return TimingLabel.USE_ON_THE_CLOCK

    # State 2: Sell now
    # Conditions: calendar is near or at peak AND team trending downward
    # OR: team in clear freefall (losing streak) with calendar heading toward peak
    calendar_near_peak = month in NEAR_PEAK_MONTHS  # {2, 3, 4}
    team_trending_down = (
        standings.last_n_wins / TRENDING_WINDOW < TRENDING_DOWN_THRESHOLD
    )
    pick_is_valuable_slot = slot <= EARLY_PICK_SLOT_THRESHOLD  # slot <= 4

    if calendar_near_peak and pick_is_valuable_slot:
        # Sell at peak window — value is high and calendar confirms it
        return TimingLabel.SELL_NOW
    if team_trending_down and standings.remaining_games > SEASON_MIDPOINT_THRESHOLD:
        # Team declining mid-season — sell before the slot gets worse
        return TimingLabel.SELL_NOW

    # State 3: Default — hold for rookie fever window
    return TimingLabel.HOLD_UNTIL_ROOKIE_FEVER
```

---

## Architecture Patterns

### Recommended Project Structure Extension

```
backend/src/fantasy/
├── picks/                           # NEW — Phase 6 engine
│   ├── __init__.py
│   ├── constants.py                 # All Phase 6 constants (named, not magic)
│   ├── models.py                    # PickValue, PickValuationContext, LeaguePickContext
│   ├── pick_engine.py               # PickEngine class — compute() method
│   └── pick_repo.py                 # DuckDB reads from picks, standings, manager_profiles
├── routers/
│   └── picks.py                     # NEW — GET /picks/{league_id} and GET /picks/{pick_id}/value
└── trade/
    └── trade_repo.py                # MODIFIED — pick value lookup redirected to PickEngine
```

### Pattern 1: Engine Class (Same as Phase 2/4/5)

**What:** `PickEngine` is a pure-Python class accepting a DuckDB connection. Stateless between calls. Does not know about HTTP.

**When to use:** All pick value computation. The router instantiates the engine and calls `compute()`.

```python
# picks/pick_engine.py
class PickEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = PickRepo(conn)

    def compute(self, pick: TradedPick, league_id: str) -> PickValue:
        context = self._build_context(pick, league_id)
        standings = self._repo.get_standings(pick.owner_roster_id, league_id)
        league_ctx = self._repo.get_league_pick_context(league_id)
        return compute_pick_value(context, standings, league_ctx)

    def compute_batch(self, picks: list[TradedPick], league_id: str) -> list[PickValue]:
        # Batch computation for league-wide pick display
        # Fetches standings and league context once, computes each pick
        ...
```

### Pattern 2: Phase 5 Integration — Pick Value Redirect

**What:** Phase 5's `TradeRepo` currently reads pick values from the Phase 2 player_values table (or a baseline approximation). Phase 6 redirects this to `PickEngine.compute()`.

**How:** `TradeRepo.get_pick_value(pick: TradedPick)` becomes a thin wrapper that instantiates `PickEngine` and calls `compute()`. The Phase 5 trade engine does not change — only the repo method changes.

```python
# trade/trade_repo.py  (MODIFIED in Phase 6)
from fantasy.picks.pick_engine import PickEngine

class TradeRepo:
    def get_pick_value(self, pick: TradedPick, league_id: str) -> float:
        # Phase 6 replaces Phase 2 baseline here
        engine = PickEngine(self._conn)
        result = engine.compute(pick, league_id)
        return result.demand_adjusted_value  # use demand-adjusted for trade evaluation
```

### Pattern 3: Database Schema for pick_values Output Table

```sql
-- pick_values: computed value per pick per league per computation run
CREATE TABLE IF NOT EXISTS pick_values (
    id                      INTEGER PRIMARY KEY,
    league_id               VARCHAR NOT NULL,
    pick_owner_roster_id    INTEGER NOT NULL,
    pick_year               INTEGER NOT NULL,
    pick_round              INTEGER NOT NULL,
    computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expected_draft_slot     FLOAT NOT NULL,
    base_value              FLOAT NOT NULL,
    timed_value             FLOAT NOT NULL,
    league_adjusted_value   FLOAT NOT NULL,
    demand_adjusted_value   FLOAT NOT NULL,
    timing_label            VARCHAR NOT NULL,  -- sell_now | hold_until_rookie_fever | use_on_the_clock
    timing_reasoning        VARCHAR NOT NULL,  -- one-line string
    class_strength_signal   FLOAT NOT NULL DEFAULT 0.0,  -- Phase 7 injection point
    computation_json        VARCHAR,           -- full input snapshot for audit/debug
    UNIQUE (league_id, pick_owner_roster_id, pick_year, pick_round)
);
```

### Pattern 4: Constants File Structure

All formula constants must be named in `picks/constants.py`. No magic numbers in engine code.

```python
# picks/constants.py

# --- Slot-to-value curve ---
SLOT_VALUE_DECAY_EXPONENT: float = 0.6      # power decay k in value = base * (1/slot)^k
FIRST_ROUND_BASE_VALUE: float = 100.0       # normalized base for 1.01

# --- Calendar timing multipliers (month: multiplier) ---
CALENDAR_TIMING_MULTIPLIERS: dict[int, float] = {
    1: 1.05,   # January — post-season, rising
    2: 1.10,   # February — draft speculation heating up
    3: 1.12,   # March — NFL free agency, class clarifying
    4: 1.18,   # April — NFL Draft week, peak rookie fever
    5: 1.08,   # May — fantasy rookie draft, still elevated
    6: 0.95,   # June — hype deflating
    7: 0.88,   # July — training camp, future uncertainty
    8: 0.87,   # August — preseason, picks discounted for immediate needs
    9: 0.85,   # September — season starts, picks cheapest
    10: 0.87,  # October — mid-season, slight uptick
    11: 0.92,  # November — trade deadline, rebuilders engaged
    12: 0.98,  # December — playoff push trades, picks moving
}
NEAR_PEAK_MONTHS: frozenset[int] = frozenset({2, 3, 4})

# --- Class strength hook ---
CLASS_STRENGTH_WEIGHT: float = 0.20  # max ±20% adjustment from class quality

# --- Rebuilder demand ---
NEUTRAL_REBUILDER_RATIO: float = 0.25   # ~3 of 12 — baseline expectation
MAX_REBUILDER_PREMIUM: float = 0.15     # maximum ±15% adjustment from rebuilder count

# --- Per-manager demand factor ---
DIRECTION_DEMAND_WEIGHT: float = 0.6   # direction label weighted more than history
HISTORY_DEMAND_WEIGHT: float = 0.4
DEMAND_HISTORY_SIGMOID_K: float = 8.0
DEMAND_HISTORY_SIGMOID_CENTER: float = 0.40   # 40% pick reception rate = neutral
DEMAND_FACTOR_MAX_PREMIUM: float = 0.10       # max ±10% adjustment from per-manager demand
MIN_TRADE_EVIDENCE_THRESHOLD: int = 10         # from Phase 4 — same constant reused

# --- Timing recommendation thresholds ---
EARLY_PICK_SLOT_THRESHOLD: int = 4       # slot ≤ 4 = "early first round" for timing logic
TRENDING_WINDOW: int = 4                 # look at last N games for trend detection
TRENDING_DOWN_THRESHOLD: float = 0.25   # fewer than 1 win in last 4 games = trending down
SEASON_MIDPOINT_THRESHOLD: int = 5      # at least 5 games remaining to trigger mid-season sell
```

### Anti-Patterns to Avoid

- **Fetching external pick values (KTC, FantasyCalc) at compute time:** Out of scope, would add external dependency, and these services don't expose the league-specific signals this engine computes. Do not build an HTTP client for pick values.
- **Computing pick value on every API call without caching:** For league-wide pick display, batch-compute and persist to `pick_values` table. Recompute on standings changes, not on every page load.
- **Using standings rank directly as draft slot:** Standings rank is discrete and ignores remaining games. Use EDP (expected draft position) formula which applies regression-to-mean for remaining season.
- **Collapsing demand_adjusted_value and league_adjusted_value into one field:** Trade evaluation uses demand-adjusted value (personalized to the buyer). League display uses league-adjusted value (neutral). Both must be stored and returned separately.
- **Hardcoding month logic inline in engine:** All calendar thresholds and multipliers live in `constants.py`. The engine reads constants, it does not embed them.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pick value from external market | Custom KTC/FantasyCalc scraper | Internal standings + formula | External values don't have league-specific signals; scraping violates ToS; this tool's edge IS the league-specific computation |
| Trend detection on standings | Custom rolling average | DuckDB window function `OVER (PARTITION BY roster_id ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)` | DuckDB handles windowed aggregation natively; no pandas/numpy needed |
| Pick slot projection simulation | Monte Carlo simulation over remaining games | Regression-to-mean formula (games_played * win_pct + remaining * 0.5) / total | Community evidence shows regression-to-mean is sufficient precision; simulation adds complexity without meaningful accuracy gain for this use case |
| Demand factor normalization | Custom normalization class | Simple sigmoid function (5 lines of math) | No library needed; sigmoid is trivial to implement and unit-test inline |

---

## Common Pitfalls

### Pitfall 1: Remaining Games = 0 Division Error
When the season is complete (remaining_games = 0), the EDP formula must use final win_pct directly without regression. Guard with: `if remaining_games == 0: return final_standings_rank`. Failure to guard this causes ZeroDivisionError mid-computation.

### Pitfall 2: Pick Year Mismatch in Multi-Year Leagues
A "2027 1st" picked up in a trade has no current standings signal — the 2027 season has not been played. The engine must handle future-year picks with a special branch: apply year-distance discount (80% per year from current, per community standard) and use a neutral slot (league_size / 2) since no standings signal exists.

```python
# Future-year pick discount
if pick.year > CURRENT_SEASON_YEAR:
    years_out = pick.year - CURRENT_SEASON_YEAR
    future_discount = FUTURE_YEAR_DISCOUNT_RATE ** years_out  # 0.80 ** years_out
    return base_value_at_neutral_slot * future_discount * calendar_mult
```
`FUTURE_YEAR_DISCOUNT_RATE = 0.80` is community consensus (MEDIUM confidence, multiple sources).

### Pitfall 3: Direction Label Absent for Manager
If Phase 4 has not been run for a league or a manager has no profile, `direction_demand_score` will be None. The engine must fall back to neutral (0.5) rather than raising KeyError. Document this as an explicit fallback in constants.

### Pitfall 4: Timing Recommendation Contradicts Phase 5 Display
Phase 5 currently shows pick value without timing context. Phase 6 adds timing inline per D-07. The planner must ensure the timing rec appears in the Phase 5 pick component, not as a separate route. Verify the Phase 5 UI pick cell is extended, not duplicated.

### Pitfall 5: Phase 7 Hook Breaks If Class Strength Weight is Zero
Setting `CLASS_STRENGTH_WEIGHT = 0.0` in Phase 6 would silently ignore Phase 7 injection. Use the default `0.20` weight and pass `class_strength_signal = 0.0`. The formula `1 + 0.20 * 0.0 = 1.0` (no change) is correct neutral behavior. This preserves Phase 7's ability to inject non-zero signals.

### Pitfall 6: League Size Assumption
Do not hardcode league_size = 12 anywhere in the engine. All slot-value computations must use `league_context.league_size` from the database. Dynasty leagues range from 8 to 16 teams; 10-team leagues have a different slot curve than 12-team.

---

## Code Examples

### DuckDB Query: Standings with Trend Window

```sql
-- pick_repo.py — get team standings with last-4-game trend
SELECT
    s.roster_id,
    s.wins,
    s.losses,
    s.wins::FLOAT / NULLIF(s.wins + s.losses, 0) AS win_pct,
    (s.total_games - s.wins - s.losses) AS remaining_games,
    SUM(CASE WHEN g.week >= (s.total_games - 3) AND g.outcome = 'win' THEN 1 ELSE 0 END)
        OVER (PARTITION BY s.roster_id) AS recent_wins
FROM standings s
LEFT JOIN weekly_results g ON g.roster_id = s.roster_id AND g.league_id = s.league_id
WHERE s.league_id = ?
  AND s.roster_id = ?
```

### DuckDB Query: League Rebuilder Count

```sql
-- pick_repo.py — count active rebuilders in league
SELECT
    league_id,
    COUNT(*) FILTER (WHERE primary_label IN ('hard_rebuild', 'elite_value_accumulation', 'one_year_punt')) AS rebuilder_count,
    COUNT(*) AS total_teams,
    COUNT(*) FILTER (WHERE primary_label IN ('hard_rebuild', 'elite_value_accumulation', 'one_year_punt'))::FLOAT / COUNT(*) AS rebuilder_ratio
FROM team_directions
WHERE league_id = ?
GROUP BY league_id
```

### DuckDB Query: Manager Pick Reception Rate

```sql
-- pick_repo.py — compute per-manager pick reception frequency
SELECT
    receiver_roster_id,
    COUNT(*) FILTER (WHERE pick_received = TRUE) AS picks_received_count,
    COUNT(*) AS total_trades,
    COUNT(*) FILTER (WHERE pick_received = TRUE)::FLOAT / NULLIF(COUNT(*), 0) AS pick_reception_rate
FROM (
    SELECT
        t.receiver_roster_id,
        MAX(CASE WHEN ta.asset_type = 'pick' AND ta.direction = 'received' THEN 1 ELSE 0 END) = 1
            AS pick_received
    FROM trades t
    JOIN trade_assets ta ON ta.trade_id = t.id
    WHERE t.league_id = ?
    GROUP BY t.id, t.receiver_roster_id
)
WHERE receiver_roster_id = ?
GROUP BY receiver_roster_id
```

### Timing Reasoning Template

```python
# picks/pick_engine.py
TIMING_REASONING_TEMPLATES: dict[str, str] = {
    "sell_now_peak_window": "Near peak rookie fever window (Apr) — sell before the draft inflates competition",
    "sell_now_trending_down": "Team trending down ({recent_wins} wins last {window} games) — sell before slot worsens",
    "hold_rookie_fever": "Calendar at buy window (Sep–Jan) — hold until April rookie fever to maximize return",
    "use_on_the_clock": "Draft in progress — use or trade immediately",
}

def compute_timing_reasoning(
    label: TimingLabel,
    standings: TeamStandingsRow,
    month: int,
) -> str:
    if label == TimingLabel.USE_ON_THE_CLOCK:
        return TIMING_REASONING_TEMPLATES["use_on_the_clock"]
    if label == TimingLabel.SELL_NOW and month in NEAR_PEAK_MONTHS:
        return TIMING_REASONING_TEMPLATES["sell_now_peak_window"]
    if label == TimingLabel.SELL_NOW:
        return TIMING_REASONING_TEMPLATES["sell_now_trending_down"].format(
            recent_wins=standings.recent_wins,
            window=TRENDING_WINDOW,
        )
    return TIMING_REASONING_TEMPLATES["hold_rookie_fever"]
```

---

## Integration: Phase 5 Pick Value Redirect

Phase 5's `TradeRepo.get_pick_value()` must be updated in Phase 6. The change is surgical — one method in one file. The trade engine's 7-dimension scoring does not change. The change is:

**Before (Phase 2 baseline):**
```python
# trade/trade_repo.py
def get_pick_value(self, pick: TradedPick, league_id: str) -> float:
    # Phase 2 baseline — placeholder value by round
    return ROUND_BASELINE_VALUES[pick.round]
```

**After (Phase 6 engine):**
```python
# trade/trade_repo.py
def get_pick_value(self, pick: TradedPick, league_id: str) -> float:
    from fantasy.picks.pick_engine import PickEngine
    engine = PickEngine(self._conn)
    result = engine.compute(pick, league_id)
    return result.demand_adjusted_value
```

This is the complete surface area of the Phase 5 integration. No other Phase 5 files change.

---

## Sources Consulted

- DynastyProcess.com pick value methodology (GAM model, perfect knowledge vs hit rate blend) — HIGH confidence
- Footballguys "Dynasty Investor: Rookie Pick Valuation" (calendar cycle timing, best buy/sell months) — HIGH confidence
- The Undroppables "Art of Dynasty Chapter 6" (rookie fever dynamics, timing strategy) — HIGH confidence
- Fantasy Footballers "Dynasty Trade Windows: Timing the Market" (month-by-month calendar breakdown, April peak, September trough) — HIGH confidence
- Adam Harstad / Footballguys "Contender/Rebuilder Dynasty Value Charts" (EVoB/EVoS framework, rebuilder discount rates) — MEDIUM confidence
- Footballguys "Six Rules for Trading Dynasty Draft Picks" (buy during season, sell during draft) — HIGH confidence
- DynastyNerds "Dynasty Trade Secrets: Understanding Draft Pick Values" (hit rate by slot tier) — MEDIUM confidence
- Fantasy Footballers "How to Value Rookie Picks in a Dynasty League" (slot-to-performance benchmarks, class strength dependency) — MEDIUM confidence

---

*Phase: 06-dynamic-pick-valuation*
*Researched: 2026-03-21*
