---
phase: 8
slug: historical-prospect-lab
status: ready
generated: 2026-03-22
---

# Phase 8 Research: Historical Prospect Lab

> Answer: What do I need to know to PLAN this phase well?
> Consumed by: gsd-planner

---

## User Constraints

**From CONTEXT.md — Locked decisions (planner MUST honor these):**

### Hit definition (PROS-01, PROS-02, PROS-03)
- D-01: Hit = finished top-X at their position for N seasons — threshold is position-specific
- D-02: Three outcome buckets: hit / mediocre / bust — mediocre is a distinct bucket, not collapsed into miss
- D-03: Timing NOT factored into historical hit definition — year-3 hit counts identically to year-1 hit

### Historical comps (PROS-04)
- D-04: Three comps per prospect: ceiling comp / median comp / floor comp — labeled by outcome role
- D-05: Comp labels are framed relative to ADP tier — ceiling/floor mean best/worst outcomes for this draft capital tier
- D-06: Each comp shows: player name, outcome bucket, one-line match reason — no peak stats
- D-07: Current class only — no UI to browse historical database; historical players surface only as named comps

### Over/undervalue flags (PROS-05)
- D-08: Divergence stated as direction + magnitude — e.g., "8 spots higher than precedent suggests"
- D-09: One net verdict per prospect ("overvalued" or "undervalued") with expandable per-signal sub-flags
- D-10: Below minimum comp count: flag shown with low-confidence label — not suppressed
- D-11: Flag is descriptive only — no suggested action or target round recommendation

### UI integration
- D-12: Outputs layer onto Phase 7 RookiePlayerCard — no new route or page
- D-13: Over/undervalue flag appears both inline (net verdict) and in an expandable section (per-signal sub-flags)
- D-14: View is data-forward — dense, sortable by model fields (tier, hit-rate bucket, ADP divergence magnitude)

### Claude's Discretion (areas where planner decides)
- Exact position-specific hit thresholds (e.g., top-12 RB for 2+ seasons = hit)
- Exact mediocre band definition per position
- Minimum comp count before low-confidence label triggers
- Feature set per position model
- Archetype clustering method and vocabulary
- Comp similarity distance metric and feature weighting
- Train/test split methodology for backtesting

### Deferred (planner MUST ignore)
- Historical prospect archive browser
- Timing-weighted hit definitions
- Suggested action on over/undervalue flag
- Cross-position hit rate comparisons

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.6.x (latest 1.6.1 as of March 2026) | Classification models, clustering, feature importance | Industry standard; covers all ML primitives needed; no heavy ML framework required for this sample size |
| nflreadpy | 0.x (active, nfl_data_py replacement) | NFL player, combine, draft, stats data loading | Official nflverse Python port; nfl_data_py archived Sep 2025 — migrate to this |
| polars | already in project | ETL, feature vector construction, aggregation | Already project-standard; faster than pandas for the aggregation patterns needed |
| duckdb | already in project | Storing processed feature vectors and model outputs | Already project-standard; all schema targets DuckDB 1.5.0 DDL |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.14.x | K-means clustering (via scipy distance metrics), statistical tests | Archetype clustering distance computation |
| numpy | already available via scikit-learn | Array operations for feature matrix | Feature scaling, normalization |

### nfl_data_py Migration Note (HIGH confidence)
nfl_data_py was **archived September 25, 2025** and is read-only. The replacement is `nflreadpy` — the Python port of nflreadr. The project already uses `nfl_data_py` in `NflDataPyLoader` (`backend/src/fantasy/ingestion/nfl_data_loader.py`). Phase 8 must use nflreadpy for any new data loading. The existing `NflDataPyLoader` still works for the already-ingested `player_stats_weekly` data because the API for `import_weekly_data()` still functions; but new function calls (combine, draft picks, players metadata) should use nflreadpy.

**Installation:**
```bash
pip install scikit-learn nflreadpy
```

**Version verification:**
```bash
pip index versions scikit-learn
pip index versions nflreadpy
```

---

## Data Sources and ETL Pipeline

### What Already Exists in DuckDB (from Phase 1)

The project already ingested 10+ years of weekly stats via `NflDataPyLoader`. The following tables are confirmed available:

| Table | Contents | Phase 8 Use |
|-------|----------|-------------|
| `player_stats_weekly` | Per-player per-week: targets, receiving_yards, receiving_tds, rushing_yards, rushing_tds, carries, passing_yards, passing_tds, fantasy_points, season, week | Seasonal rollup for production features (market share, efficiency) |
| `players` | player_id, full_name, position, team, age, metadata_blob | Player identity, position filter — primary key for joining |
| `player_adp_baseline` | player_id, player_name, position, adp | Dynasty ADP baseline for divergence magnitude computation |

### What Must Be Fetched in Phase 8 (via nflreadpy)

| Data | Function | Key Columns | Phase 8 Use |
|------|----------|-------------|-------------|
| Combine measurements | `nflreadpy.load_combine(seasons=list)` | `player_name`, `pos`, `ht`, `wt`, `forty`, `vertical`, `cone`, `shuttle`, `bench`, `draft_ovr`, `draft_round`, `draft_year`, `school` | Athletic testing features; draft capital features |
| Player bio + draft info | `nflreadpy.load_players()` | `gsis_id`, `display_name`, `birth_date`, `college_name`, `rookie_season`, `draft_year`, `draft_round`, `draft_pick` | Age at draft calculation; player identity cross-reference |
| Draft picks | `nflreadpy.load_draft_picks(seasons=list)` | `season`, `round`, `pick`, `gsis_id`, `pfr_id`, `position` | Draft slot (overall pick number) for ADP tier bucketing |

### College Production Gap (MEDIUM confidence)

nflreadpy does **not** include college production data (target share, yards per game, dominator rating). College stats come from a separate ecosystem:

- **CollegeFootballData.com** (`collegefootballdata.com`) — REST API with CFB player stats, target data; requires free API key
- **cfbfastR** (R package) / no Python equivalent — R users access CFB data this way
- **sportyR / cfbd-python** — Unofficial Python wrappers for `collegefootballdata.com`

**Recommended approach:** Use the `collegefootballdata.com` API directly via `httpx` or `requests`. The project already has async HTTP infrastructure via Sleeper client (`sleeper_client.py`). A `CFBDataClient` follows the same pattern.

Key college metrics needed per prospect (PROS-02):
- `receiving_yards`, `receiving_tds`, `receptions` — last 1-2 college seasons
- `targets` (if available — not all CFB data sources have targets)
- `rush_yards`, `rush_att` for RBs
- `games_played` — to normalize per-game
- Denominator for market share: team pass attempts or team receiving yards that season

**Alternative for market share if CFB API data is unavailable:** Derive a proxy from the combine data's `school` column cross-referenced against team-level CFB stats. This is a fallback — attempt the CFB API first.

---

## Architecture Patterns

### Recommended Package Structure

Following the Phase 6 `picks/` engine pattern and Phase 4 `profiling/` pattern:

```
backend/src/fantasy/
├── prospects/
│   ├── __init__.py
│   ├── constants.py          # HIT thresholds, MEDIOCRE bands, MIN_COMP_COUNT, feature weights
│   ├── models.py             # Pydantic models: ProspectFeatures, ProspectModelOutput, HistoricalComp
│   ├── feature_builder.py    # Builds feature vectors from raw tables for historical + current class
│   ├── hit_classifier.py     # Three-bucket hit/mediocre/bust labeling engine
│   ├── prospect_model.py     # Position-specific model training, backtesting, feature importance
│   ├── archetype_clusterer.py # K-means or rule-based archetype assignment
│   ├── comp_finder.py        # Finds ceiling/median/floor comps per prospect
│   ├── divergence_engine.py  # Computes over/undervalue flag + per-signal sub-flags
│   └── prospect_repo.py      # DuckDB reads/writes for prospect tables
```

### New DuckDB Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `historical_prospect_features` | One row per player-draft-year with all model input features | `player_id`, `draft_year`, `position`, `age_at_draft`, `draft_ovr`, `forty`, `wt`, `ht`, `vertical`, `college_rec_yards_pg`, `college_mkt_share_proxy`, `college_td_rate`, `season_1_fp`, `season_2_fp`, `season_3_fp`, `outcome_bucket` |
| `prospect_model_outputs` | Current class: model scores, archetype, comps, flag | `player_id`, `position`, `archetype_label`, `hit_rate_bucket`, `tier`, `risk_band`, `ceiling_comp_id`, `median_comp_id`, `floor_comp_id`, `overvalue_flag_direction`, `overvalue_magnitude`, `low_confidence`, `computed_at` |
| `prospect_sub_flags` | Per-signal sub-flags for the expandable panel | `player_id`, `signal_name`, `direction`, `magnitude_str`, `computed_at` |

### Pattern 1: Time-Based Train/Test Split (PROS-02, PROS-03)

**What:** Walk-forward validation on historical cohorts.
**When to use:** Any time a claim is made about model-derived feature weights.
**Methodology:**
- Group prospects by `draft_year`
- Training set: draft years 2011 through Y-3 (e.g., 2011–2020 for a 2023 test year)
- Test set: one draft cohort at a time, rolling forward
- Minimum 3 post-draft seasons for outcome labeling — prospects with fewer than 3 seasons cannot have confirmed outcome buckets assigned
- This means seasons 2011–2018 are the earliest usable training cohorts (need outcome data through 2021)
- Never include the current draft class (2025/2026) in any training split — these have no outcomes yet

**Implementation:**
```python
# Walk-forward split example
all_cohorts = sorted(df["draft_year"].unique())  # e.g., 2011–2022
for test_year_idx in range(3, len(all_cohorts)):  # start at index 3 for minimum train size
    train_years = all_cohorts[:test_year_idx]
    test_year = all_cohorts[test_year_idx]
    train_df = df[df["draft_year"].isin(train_years)]
    test_df = df[df["draft_year"] == test_year]
    # fit model on train_df, evaluate on test_df
```

**Key constraint:** A player needs 3 full seasons to confirm outcome. 2022 draft class needs outcomes through 2024. Season 2024 data is available in nflreadpy. This means the 2022 class is the most recent cohort with confirmable outcomes as of March 2026.

### Pattern 2: Position-Specific Logistic Regression (PROS-02)

**What:** Multinomial logistic regression (or Random Forest) per position predicting hit/mediocre/bust.
**When to use:** Ordered three-class outcome with small N per position.

**Sample size reality (LOW confidence — estimated from public knowledge):**
- NFL rookie class: ~220–250 skill positions per year
- QB class: ~10–20 per year; RB: ~40–60; WR: ~70–100; TE: ~25–40
- With 10+ years of history (2011–2022 = ~12 cohorts for confirmed outcomes): QB ~120–240 total, RB ~480–720, WR ~840–1200, TE ~300–480
- **QB is the highest-risk position for overfitting** — consider regularized logistic regression (L2) or explicit feature pruning for QB model

**Recommended approach per position:**
- RB, WR, TE: Random Forest with permutation feature importance (handles nonlinear interactions, provides feature weights, more robust to small N than gradient boosting)
- QB: Logistic Regression with L2 regularization (lower N, simpler model preferred)
- All positions: cross-validate feature weights via the walk-forward split; do not use a single train/test split for weight derivation

**Key finding:** Permutation feature importance from scikit-learn's `permutation_importance()` is preferred over impurity-based importance for Random Forest when N is small — impurity-based importance overstates high-cardinality features. Permutation importance is model-agnostic and produces feature weights that satisfy PROS-02 ("weights derived from backtesting, not hardcoded assumptions").

**Example (verified against scikit-learn 1.6 docs):**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

clf = RandomForestClassifier(n_estimators=200, max_features="sqrt", random_state=42)
clf.fit(X_train, y_train)
result = permutation_importance(clf, X_val, y_val, n_repeats=30, random_state=42)
feature_weights = result.importances_mean  # array, one weight per feature
```

### Pattern 3: K-Means Archetype Clustering (PROS-03)

**What:** Cluster historical prospects by feature vector into N archetypes per position.
**When to use:** Assigning archetype labels for current class.

**Recommended approach:**
- Cluster on a subset of features (exclude outcome features — cluster on entry characteristics only): age, size metrics, testing metrics, production proxy
- K = 3–5 per position (Claude's Discretion per context D in CONTEXT.md)
- Use `sklearn.cluster.KMeans` with `n_init=10`, scale features with `StandardScaler` first
- Archetype labels are manually named after inspecting cluster centroids — not algorithmic
- Store cluster centroids in `constants.py`; assignment at inference time uses `kmeans.predict()` on new prospect feature vector

**Anti-pattern:** Do not cluster on outcome features — this leaks the answer into the archetype and makes comp assignment circular.

### Pattern 4: Comp Finding (PROS-04)

**What:** For each current prospect, find the three historical closest neighbors by feature distance, then select ceiling/median/floor from their outcomes.
**Methodology:**
- Compute Euclidean distance in the scaled feature space used for clustering (same feature subset)
- Filter candidates to same position AND same ADP draft capital tier (bucket the historical player's `draft_ovr` into tiers: picks 1–12 = Tier 1, 13–36 = Tier 2, 37–72 = Day 2, 73–255 = Day 3) — this satisfies D-05 (comps relative to draft capital tier)
- From the nearest N candidates (e.g., 10–20), select:
  - **Ceiling comp**: nearest neighbor in tier with outcome = hit
  - **Floor comp**: nearest neighbor in tier with outcome = bust
  - **Median comp**: nearest neighbor in tier with outcome = mediocre (if none, next-nearest with hit or bust by distance rank)
- Match reason string is generated from which features drove closest distance — top 2–3 features by distance contribution become the one-line reason

### Pattern 5: Over/Undervalue Flag (PROS-05)

**What:** Compare current player's ADP to the historical median ADP of players with the same archetype + outcome profile.
**Methodology:**
- For each prospect: find all historical comps in the same ADP tier + archetype bucket
- Compute the median dynasty ADP for hit outcomes vs. current ADP
- Divergence magnitude = `current_adp - historical_median_adp_for_hits` in same tier
  - Positive = overvalued (paying more than historical precedent for hit outcomes)
  - Negative = undervalued
- Per-signal sub-flags: for each feature input (age, draft capital, production, testing), compute the prospect's z-score against the archetype cluster median — flag direction (positive/negative) and magnitude string
- Low-confidence trigger: when fewer than `MIN_COMP_COUNT` historical players exist in the same tier + archetype bucket, set `low_confidence = True`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Feature importance | Custom weight calculation | `sklearn.inspection.permutation_importance` | Avoids impurity bias; handles multicollinearity; single correct implementation |
| Train/test splitting | Custom year-loop logic | `sklearn.model_selection` primitives + manual year filter | Use sklearn's pipeline but apply the year-based split explicitly to avoid leakage |
| Feature scaling | Manual min-max formulas | `sklearn.preprocessing.StandardScaler` with `.fit()` on train only, `.transform()` on test | Prevents data leakage from test set into scaling parameters |
| Distance computation for comps | Nested loops with Euclidean formula | `scipy.spatial.distance.cdist` or `sklearn.metrics.pairwise.euclidean_distances` | Vectorized, tested, handles edge cases |
| K-means clustering | Custom centroid iteration | `sklearn.cluster.KMeans` | Convergence guarantees, reproducible with `random_state` |
| NFL data loading | Custom HTTP to nflverse endpoints | `nflreadpy.load_combine()`, `load_players()`, `load_draft_picks()` | Handles caching, parquet format, versioned data |

**Key insight:** The prospect lab is an internal analytics tool, not a production ML serving system. Prioritize correctness of methodology over ML sophistication. A well-specified logistic regression with walk-forward validated weights is more trustworthy than an over-engineered gradient boosting stack on 300 observations.

---

## Common Pitfalls

### 1. Look-Ahead Bias in Feature Construction
**What:** Using outcome data (NFL fantasy points) to construct features that are then used to train the model.
**How it happens:** Rolling up a player's career fantasy points across all seasons, then using that as a feature.
**Prevention:** Feature vectors for the historical model must contain **only pre-draft information**: age, combine, draft slot, college production. NFL career outcomes are the labels only — never features.

### 2. Insufficient Seasons for Outcome Labeling
**What:** Labeling a prospect as bust/mediocre when they only have 1–2 seasons of data.
**How it happens:** Including the 2023 or 2024 draft class in training with incomplete outcome data.
**Prevention:** Enforce a minimum 3-season window. Filter `historical_prospect_features` to only include players with `max_season - draft_year >= 3` before computing outcome bucket. Add this check as a named constant `MIN_OUTCOME_SEASONS = 3`.

### 3. nfl_data_py vs. nflreadpy API Mismatch
**What:** Phase 8 code calls `nfl.import_combine_data()` (old API) — this still works today but the repo is archived.
**Prevention:** Use `nflreadpy.load_combine()` for all new Phase 8 data loading. The function signatures differ; do not assume old API parameters carry over. The existing `NflDataPyLoader` in the project is fine for `player_stats_weekly` data already loaded in Phase 1, but all new Phase 8 data loads should use nflreadpy.

### 4. College Production Data Not in nflreadpy
**What:** Assuming nflreadpy provides college target share, yards per game, or market share — it does not.
**Prevention:** College production requires a separate source (CollegeFootballData.com API). Plan a `CFBDataClient` analogous to `SleeperClient`. This is a new dependency that must be in the plan. If CFB API data is unavailable or spotty, the model gracefully degrades by excluding college production features for affected players (surfaced as a data gap per the project's gap detection pattern).

### 5. Draft Capital Tier vs. ADP Conflation
**What:** Using `draft_ovr` (NFL draft pick slot) and dynasty `adp` interchangeably.
**Prevention:** These are different signals. `draft_ovr` from the combine/draft picks data = NFL draft position (1–256). Dynasty `adp` from `player_adp_baseline` = dynasty fantasy draft value. Both are inputs to the model; keep them as separate features with separate column names. The over/undervalue flag divergence is computed against dynasty `adp`, not NFL draft slot.

### 6. Overfitting on QB Model
**What:** Training a Random Forest on 150 QBs produces apparent feature importances that don't generalize.
**Prevention:** For QB, use logistic regression with `C=0.1` (strong L2 regularization) and limit features to 3–5 most theoretically motivated predictors (age, draft_ovr, forty, college_completion_pct proxy if available). Validate with walk-forward; if test accuracy < 55% on QBs, report the model as low-confidence for that position.

### 7. Missing Combine Data (Not All Prospects Attend)
**What:** Roughly 15–20% of drafted skill players have missing combine measurements.
**Prevention:** Impute missing testing values with position-specific medians (from the training set). Use `sklearn.impute.SimpleImputer` with `strategy='median'`. Do not drop these players — they are valid historical data points. Flag imputed features in constants for transparency.

### 8. Player ID Mapping Across Sources
**What:** `player_stats_weekly` uses `gsis_id` from nfl_data_py; `load_combine()` returns `pfr_id` and `player_name`. Joining these without a cross-reference table produces silent mismatches.
**Prevention:** Use `nflreadpy.load_players()` which returns all ID mappings (`gsis_id`, `pfr_id`, `espn_id`, `nfl_id`). Build a canonical ID map table (`prospect_id_map`) early in the ETL, then join everything through it.

---

## Code Examples

### nflreadpy Data Loading Pattern
```python
# Source: nflreadpy official docs — https://nflreadpy.nflverse.com/
import nflreadpy as nfl

# Load combine data for historical years
combine_df = nfl.load_combine(seasons=list(range(2011, 2026)))

# Load player bio + draft info
players_df = nfl.load_players()

# Load draft picks for historical seasons
draft_df = nfl.load_draft_picks(seasons=list(range(2011, 2026)))
```

### DuckDB Upsert Pattern (follows existing project convention)
```python
# Source: established pattern from league_repo.py and pick_repo.py
conn.register("features_df", polars_df)
conn.execute("""
    INSERT INTO historical_prospect_features
    SELECT * FROM features_df
    ON CONFLICT (player_id, draft_year) DO UPDATE SET
        outcome_bucket = EXCLUDED.outcome_bucket,
        ...
""")
conn.unregister("features_df")
```

### FastAPI Router Registration (follows existing pattern)
```python
# Source: backend/src/fantasy/main.py — existing app factory pattern
from fantasy.routers import prospects
app.include_router(prospects.router, prefix="/prospects", tags=["prospects"])
```

### Low-Confidence Pattern (follows Phase 4 convention)
```python
# Source: backend/src/fantasy/profiling/constants.py pattern
# In prospects/constants.py:
MIN_COMP_COUNT = 5  # below this, over/undervalue flag shows low-confidence label
```

---

## API Endpoint Specification

Two new endpoints required (per 08-UI-SPEC.md):

| Endpoint | Method | Returns |
|----------|--------|---------|
| `GET /prospects/model-outputs/{league_id}` | GET | List of `ProspectModelOutput` objects — one per current class player; includes archetype_label, hit_rate_bucket, overvalue_flag_direction, overvalue_magnitude, low_confidence, sub_flags |
| `GET /prospects/comps/{player_id}` | GET | Three `HistoricalComp` objects — ceiling/median/floor for the named player |

Per 08-UI-SPEC.md: Phase 7 data comes from `GET /rookie-board/{league_id}`; Phase 8 model outputs come separately from `GET /prospects/model-outputs/{league_id}`. Client joins by `player_id`. These are two separate TanStack Query calls with different `staleTime` values (15 min vs. 30 min).

---

## Position-Specific Hit Threshold Recommendations

(Claude's Discretion per CONTEXT.md — these are evidence-informed recommendations for the planner to use as defaults)

| Position | Hit Definition | Mediocre Band | Bust |
|----------|---------------|--------------|------|
| QB | Top-6 fantasy QB in 2+ of first 4 seasons | Top-6 in exactly 1 of first 4 seasons | Never reached top-6 |
| RB | Top-12 fantasy RB in 2+ of first 3 seasons | Top-24 but not top-12 in at least 1 of first 3 seasons | Below top-24 in all of first 3 seasons |
| WR | Top-24 fantasy WR in 2+ of first 4 seasons | Top-36 but not top-24 in at least 1 of first 4 seasons | Below top-36 in all of first 4 seasons |
| TE | Top-12 fantasy TE in 2+ of first 4 seasons | Top-24 but not top-12 in at least 1 of first 4 seasons | Below top-24 in all of first 4 seasons |

**Rationale:** RBs use a 3-season window (career compression is real; 4-year window would misclassify many valid RB hits as mediocre). WRs and TEs use 4-season window (development curve is longer). QBs use 4 seasons with a tighter top-6 threshold (dynasty value is concentrated at elite starters). These thresholds are named constants in `prospects/constants.py` and can be adjusted without code changes.

**Recommended `MIN_COMP_COUNT = 5`:** Below 5 historical comps in the same tier + archetype, the low-confidence label triggers. This matches the spirit of Phase 4's `MIN_TRADE_EVIDENCE_THRESHOLD = 10` (proportional — fewer total archetypes per position than manager trades).

---

## Key Decisions for Planner

1. **CFB API integration scope:** Decide whether college production features are required in the first plan wave or deferred to a second wave. If deferred, the feature model runs without college production features and degrades gracefully. This is a significant scope decision because a `CFBDataClient` is a non-trivial addition.

2. **Model training trigger:** The position models must be re-trained when new season data is added. Decide whether model training runs: (a) as a CLI script triggered manually, (b) on ingest completion, or (c) on-demand via an API endpoint. Recommendation: CLI script matching the project's on-demand philosophy.

3. **`prospect_model_cache` vs. extending `rookie_board_cache`:** The context notes the planner should decide. Recommendation: a separate `prospect_model_outputs` table (not extending the Phase 7 table), because model recomputation cadence differs from board cache, and the schemas diverge significantly.

4. **Alembic migration number:** Phase 7 will have consumed migration slots. Phase 8 adds 3 new tables (`historical_prospect_features`, `prospect_model_outputs`, `prospect_sub_flags`) in a single migration. The planner must assign the correct migration number after confirming Phase 7's final migration count.

---

## Confidence Summary

| Finding | Confidence | Source |
|---------|------------|--------|
| nfl_data_py archived Sep 2025; nflreadpy is the replacement | HIGH | Official nflverse GitHub |
| nflreadpy provides `load_combine()`, `load_players()`, `load_draft_picks()` | HIGH | nflreadpy official docs |
| `load_combine()` returns 18 columns including physical measurements and draft_ovr | HIGH | nflreadr reference docs |
| `load_players()` returns 39 columns including birth_date, college_name, draft info | HIGH | nflreadr reference docs |
| College production data NOT in nflreadpy — requires CollegeFootballData.com separately | HIGH | Confirmed absence from nflreadpy docs |
| Walk-forward validation is correct methodology for time-series model backtesting | HIGH | MachineLearningMastery.com + general ML literature |
| Permutation importance preferred over impurity-based importance for small N | MEDIUM | scikit-learn docs + multiple ML sources |
| Estimated prospect sample sizes per position per year (for overfitting risk assessment) | LOW | Estimated from general NFL draft knowledge; validate by querying actual data |
| Proposed hit thresholds (top-12 RB, top-24 WR, etc.) | MEDIUM | Standard dynasty community conventions; should be validated against actual hit-rate distributions after feature table is built |

---

## Sources

- [nflreadpy official docs](https://nflreadpy.nflverse.com/)
- [nflreadpy load_functions reference](https://nflreadpy.nflverse.com/api/load_functions/)
- [nflreadr load_combine reference](https://nflreadr.nflverse.com/reference/load_combine.html)
- [nflreadr load_players reference](https://nflreadr.nflverse.com/reference/load_players.html)
- [nfl_data_py GitHub (archived)](https://github.com/nflverse/nfl_data_py)
- [nflreadpy GitHub](https://github.com/nflverse/nflreadpy)
- [scikit-learn permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html)
- [scikit-learn RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [How to Backtest ML Models for Time Series — MachineLearningMastery.com](https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/)
- [DynastyProcess data repository](https://github.com/dynastyprocess/data)
