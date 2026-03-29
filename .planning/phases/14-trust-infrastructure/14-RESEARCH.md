# Phase 14: Trust Infrastructure — Research

**Phase goal:** No connected league silently receives high-confidence advice under rules the tool does not actually model.

**Requirement:** FS-07

---

## User Constraints

No CONTEXT.md exists for this phase. All decisions below are researcher recommendations; none are locked by prior user discussion.

---

## Key Findings from Codebase Inspection

### What exists today (HIGH confidence — directly verified)

The `settings_blob` column on the `leagues` table stores the full Sleeper `settings` object as a JSON string. It is ingested by `SleeperMapper.map_league` and stored verbatim, but **zero backend code reads it after ingest**. No engine currently inspects `settings_blob` to detect format variants.

The `scoring_settings` column likewise stores the full Sleeper scoring object as a JSON string. It is partially consumed by `SleeperMapper` to detect `ppr` (via `rec`) and `tep` (via `bonus_rec_te`), and by `ValuationEngine` via `FORMAT_MULTIPLIERS`. All other scoring keys are ignored.

The `roster_positions` column stores a JSON list of position strings. `SleeperMapper` checks for `"SUPER_FLEX"` in the list. No code checks for IDP position strings (`DL`, `LB`, `DB`, `IDP_FLEX`, `EDGE`, `CB`, `S`).

Both live leagues in the database use: `type=2` (dynasty), `best_ball=0`, `league_average_match=1` (median wins enabled), `bonus_rec_te=0.5` (TE premium), `rec=0.5` (half-PPR), `SUPER_FLEX` in roster_positions.

**Critical gap:** `league_average_match=1` is present in both connected leagues right now and is not modeled by any engine. The tool is already giving advice to leagues using median wins without flagging it.

---

## Sleeper API: Format Detection Fields

**Source:** Live API call against real connected leagues + official Sleeper settings blob (HIGH confidence for fields observed; MEDIUM confidence for fields inferred from community tools).

### `settings` blob keys relevant to trust classification

| Key | Type | Observed values | What it signals |
|-----|------|-----------------|-----------------|
| `type` | int | `0`=redraft, `1`=keeper, `2`=dynasty | League type (dynasty tool assumes 2; other values are unsupported) |
| `best_ball` | int | `0`/`1` | Best ball mode — auto-starts optimal lineup; no lineup management; changes all decision logic |
| `league_average_match` | int | `0`/`1` | Median wins enabled — extra W/L vs. league median each week |
| `salary_cap` | int | `0`/`1` | Salary cap enabled — contract values affect all trade/value logic |
| `taxi_slots` | int | 0–N | Taxi squad size (already used by Phase 11) |
| `taxi_years` | int | 0–N | Taxi eligibility window (already used by Phase 11) |
| `taxi_allow_vets` | int | 0/1 | Whether vets can be placed on taxi |

Note: `waiver_budget` being set to a non-zero value does NOT alone indicate salary cap league. Salary cap (contract-based) leagues use a separate `salary_cap` flag. `waiver_budget` is FAAB.

### `scoring_settings` keys relevant to trust classification

| Key | Meaning | Materially affects |
|-----|---------|-------------------|
| `rec` | PPR value (0.0, 0.5, 1.0) | Already modeled via FORMAT_MULTIPLIERS |
| `bonus_rec_te` | TE reception bonus | Already modeled via FORMAT_MULTIPLIERS |
| `bonus_rec_wr` | WR reception bonus (rare variant) | NOT modeled — changes WR scarcity |
| `bonus_rec_rb` | RB reception bonus | NOT modeled |
| `rush_fd` | Points per rushing first down | NOT modeled — materially changes RB value |
| `rec_fd` | Points per receiving first down | NOT modeled — materially changes WR/TE value |
| `pass_fd` | Points per passing first down | NOT modeled — changes QB value |
| `ret_yd` | Return yards scoring | NOT modeled — changes returner/flex value |
| `kr_td` | Kick return TD | NOT modeled |
| `pr_td` | Punt return TD | NOT modeled |

**Confirmed from live leagues:** Neither connected league uses first-down scoring or return scoring. Both have `rush_fd`, `rec_fd`, `pass_fd`, `ret_yd` absent from scoring_settings (zero or missing is equivalent).

### `roster_positions` strings relevant to trust classification

| String(s) | What it signals |
|-----------|----------------|
| `SUPER_FLEX` | Superflex — already detected and modeled |
| `DL`, `LB`, `DB`, `IDP_FLEX`, `EDGE`, `CB`, `S` | IDP — not modeled at all |
| `DEF` | Team defense — standard; already tolerated |
| `K` | Kicker — standard; already tolerated |

**IDP detection rule:** Any roster_positions list containing `DL`, `LB`, `DB`, `IDP_FLEX`, `EDGE`, `CB`, or `S` indicates an IDP league. IDP fundamentally changes player pool composition, defensive player values, and roster construction logic — none of which the tool models.

### Devy detection

Devy leagues (developmental players — college prospects rostered before draft eligibility) appear as distinct player entries in Sleeper's player database with `"status": "inactive"` or a `"years_exp"` of -1 to -3. Devy is detected by whether any rostered player has negative `years_exp` or a college team rather than NFL team. There is no dedicated `devy` key in the `settings` blob that the API exposes.

**Confidence:** MEDIUM (inferred from community tools; Sleeper docs do not document this explicitly).

### Empire format detection

Empire is a third-party format concept (one manager owns all teams) not supported as a native Sleeper format type. If it exists on Sleeper, it would appear as `type=2` with unusual `num_teams` or commissioner configuration. No reliable Sleeper API key signals empire. **Treat empire as out of scope** for automated detection — document as "manual flag" only.

---

## Standard Stack

All new code follows the established project stack. No new third-party libraries are required for Phase 14.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic v2 | `~2.x` (project baseline) | Rule support matrix models, API response models | Already the domain model layer for all engines |
| DuckDB | `~1.1.x` (project baseline) | Persist format scan results and acknowledgment flags | The project DB; no SQLite or alternate stores |
| FastAPI | `~0.115.x` (project baseline) | New `/trust` router for scan endpoints and acknowledgment CRUD | Existing router pattern |
| React 19 + shadcn-ui | project baseline | Warning banner component | `ConcentrationAlertBanner` is the direct pattern to follow |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing.Literal` | stdlib | Classify support levels (`"supported"`, `"partially_supported"`, `"unsupported"`) | All rule classification type aliases follow this project pattern (see `HYGIENE_ACTION_TYPES`, `TITLE_WINDOW_LABELS`) |
| Python `enum.Enum` | stdlib | FormatRule enum registry (one entry per detectable rule) | Only for the rule identifier constants; classification level uses Literal |

**No new pip installs required for Phase 14.**

---

## Architecture Patterns

### Pattern 1: Enum-based Rule Registry with Pydantic Classification Model

**What:** Define one Python `StrEnum` or `str + Enum` constant per detectable format rule. Each rule entry maps to a `RuleSupportLevel` Literal. A `RuleScanResult` Pydantic model holds the per-rule verdict plus a human-readable reason and a `distorts_recommendations` flag.

**Why this pattern:** The project already uses Literal-based contracts (see `HYGIENE_ACTION_TYPES` in `lineup/constants.py`) and enum-keyed weight tables (see `DIRECTION_WEIGHTS` in `intelligence/constants.py`). A rule registry follows the same pattern, keeping all classification logic in constants and pure functions — not scattered across engine code.

**Example:**

```python
# trust/constants.py
from __future__ import annotations
from enum import StrEnum
from typing import Literal

RuleSupportLevel = Literal["supported", "partially_supported", "unsupported"]

class FormatRule(StrEnum):
    SUPERFLEX        = "superflex"
    TEP              = "tep"
    HALF_PPR         = "half_ppr"
    FULL_PPR         = "full_ppr"
    STANDARD         = "standard"
    MEDIAN_WINS      = "median_wins"
    BEST_BALL        = "best_ball"
    IDP              = "idp"
    SALARY_CAP       = "salary_cap"
    DEVY             = "devy"
    FIRST_DOWN_SCORING = "first_down_scoring"
    RETURN_SCORING   = "return_scoring"
    WR_BONUS         = "wr_bonus"
    NON_DYNASTY      = "non_dynasty"

# Support matrix: each rule -> (level, short_reason, distorts_recs)
RULE_SUPPORT_MATRIX: dict[FormatRule, tuple[RuleSupportLevel, str, bool]] = {
    FormatRule.SUPERFLEX:          ("supported",          "Fully modeled", False),
    FormatRule.TEP:                ("supported",          "TE bonus modeled in valuation", False),
    FormatRule.HALF_PPR:           ("supported",          "Half-PPR modeled", False),
    FormatRule.FULL_PPR:           ("supported",          "Full-PPR modeled", False),
    FormatRule.STANDARD:           ("supported",          "Standard scoring modeled", False),
    FormatRule.MEDIAN_WINS:        ("partially_supported","Win-now urgency not median-adjusted", True),
    FormatRule.BEST_BALL:          ("unsupported",        "Best ball changes all lineup logic", True),
    FormatRule.IDP:                ("unsupported",        "Defensive players not valued", True),
    FormatRule.SALARY_CAP:         ("unsupported",        "Contract constraints not modeled", True),
    FormatRule.DEVY:               ("unsupported",        "College prospects not in player pool", True),
    FormatRule.FIRST_DOWN_SCORING: ("partially_supported","First-down value not in player scores", True),
    FormatRule.RETURN_SCORING:     ("partially_supported","Return specialist value not modeled", True),
    FormatRule.WR_BONUS:           ("partially_supported","WR bonus not reflected in positional multipliers", True),
    FormatRule.NON_DYNASTY:        ("unsupported",        "Tool is dynasty-only; pick/youth values invalid", True),
}
```

### Pattern 2: League Scanner Function

**What:** A pure function `scan_league_format(settings: LeagueSettings) -> LeagueFormatScan` reads from the already-ingested `LeagueSettings` domain model (which has `scoring_settings`, `roster_positions`, `settings_blob`) and emits a list of `RuleScanEntry` items — one per detected non-trivial rule.

**Key design decisions:**
- The scanner only reports rules that are PRESENT in the league. If `best_ball=0`, the scanner does not emit a `best_ball` entry at all.
- The scanner always emits at least one entry for the scoring type (ppr/half_ppr/standard) and dynasty type.
- The scanner is stateless and dependency-free — no DB access, no engine calls.

```python
# trust/scanner.py
from fantasy.ingestion.sleeper_mapper import LeagueSettings
from fantasy.trust.constants import FormatRule, RULE_SUPPORT_MATRIX
from fantasy.trust.models import RuleScanEntry, LeagueFormatScan

IDP_POSITION_STRINGS = {"DL", "LB", "DB", "IDP_FLEX", "EDGE", "CB", "S"}

def scan_league_format(settings: LeagueSettings) -> LeagueFormatScan:
    sb = settings.settings_blob  # dict[str, Any]
    ss = settings.scoring_settings  # dict[str, float]
    rp = set(settings.roster_positions)

    detected: list[FormatRule] = []

    # Dynasty type
    if sb.get("type", 2) != 2:
        detected.append(FormatRule.NON_DYNASTY)

    # Scoring type (always emit one)
    if settings.ppr >= 1.0:
        detected.append(FormatRule.FULL_PPR)
    elif settings.ppr >= 0.5:
        detected.append(FormatRule.HALF_PPR)
    else:
        detected.append(FormatRule.STANDARD)

    # Already-modeled format flags
    if settings.superflex:
        detected.append(FormatRule.SUPERFLEX)
    if settings.tep:
        detected.append(FormatRule.TEP)

    # Partially/unsupported format flags
    if sb.get("league_average_match", 0):
        detected.append(FormatRule.MEDIAN_WINS)
    if sb.get("best_ball", 0):
        detected.append(FormatRule.BEST_BALL)
    if sb.get("salary_cap", 0):
        detected.append(FormatRule.SALARY_CAP)
    if rp & IDP_POSITION_STRINGS:
        detected.append(FormatRule.IDP)
    if ss.get("rush_fd", 0.0) or ss.get("rec_fd", 0.0) or ss.get("pass_fd", 0.0):
        detected.append(FormatRule.FIRST_DOWN_SCORING)
    if ss.get("ret_yd", 0.0) or ss.get("kr_td", 0.0) or ss.get("pr_td", 0.0):
        detected.append(FormatRule.RETURN_SCORING)
    if ss.get("bonus_rec_wr", 0.0):
        detected.append(FormatRule.WR_BONUS)

    entries = [
        RuleScanEntry(
            rule=r,
            support_level=RULE_SUPPORT_MATRIX[r][0],
            reason=RULE_SUPPORT_MATRIX[r][1],
            distorts_recommendations=RULE_SUPPORT_MATRIX[r][2],
        )
        for r in detected
    ]
    needs_ack = any(e.support_level == "partially_supported" and e.distorts_recommendations for e in entries)
    league_unsupported = any(e.support_level == "unsupported" for e in entries)
    return LeagueFormatScan(
        league_id=settings.league_id,
        entries=entries,
        needs_acknowledgment=needs_ack,
        league_unsupported=league_unsupported,
    )
```

### Pattern 3: Pydantic Models for Trust Layer

```python
# trust/models.py
from pydantic import BaseModel, ConfigDict
from fantasy.trust.constants import FormatRule, RuleSupportLevel

class RuleScanEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    rule: str              # FormatRule value
    support_level: RuleSupportLevel
    reason: str
    distorts_recommendations: bool

class LeagueFormatScan(BaseModel):
    model_config = ConfigDict(frozen=True)
    league_id: str
    entries: list[RuleScanEntry]
    needs_acknowledgment: bool   # True if any partially_supported+distorts
    league_unsupported: bool     # True if any unsupported entry exists

class FormatAcknowledgment(BaseModel):
    model_config = ConfigDict(frozen=False)
    league_id: str
    acknowledged_rules: list[str]  # list of FormatRule values the user has acked
    acknowledged_at: str           # ISO timestamp
```

### Pattern 4: Persistent Acknowledgment Storage (DuckDB table)

**What:** Single table `league_format_acknowledgments` with one row per league. When user clicks "I understand, continue" on the partial-support banner, the frontend POSTs to `/trust/{league_id}/acknowledge` and the backend upserts the row. The flag persists across server restarts and sessions.

**Why persistent over session-level:** This is a local single-user tool. Session-level storage (cookies, in-memory) would require re-acknowledgment on every server restart. A DuckDB table costs one upsert and is consistent with how all other per-league config (taxi, draft order rules) is stored.

```sql
CREATE TABLE IF NOT EXISTS league_format_acknowledgments (
    id                  INTEGER PRIMARY KEY,
    league_id           VARCHAR NOT NULL UNIQUE,
    acknowledged_rules  VARCHAR NOT NULL,  -- JSON list of rule strings
    acknowledged_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Invalidation rule:** When a new ingest run completes for a league, re-scan the format. If the scan result differs from the previously acknowledged rule set (new rules found, or previously-flagged rules are now gone), clear the acknowledgment and require re-acknowledgment.

### Pattern 5: Confidence Degradation via Confidence Multiplier

**What:** Each engine result that is affected by partially supported rules receives a `trust_modifier` float (0.0 to 1.0). The modifier is computed once per league from the `LeagueFormatScan` and passed to downstream engine computations. For fully supported leagues, `trust_modifier = 1.0`. For leagues with unacknowledged partially supported rules, `trust_modifier = 0.75`. For leagues with unsupported rules, `trust_modifier = 0.50`.

**Where to apply:** The modifier is NOT applied inside engine internals. Instead, it is applied at the API response layer to the `confidence_score` fields and `confidence_band` labels before they are returned. This keeps engine code clean and makes the degradation observable.

```python
# trust/confidence.py
from fantasy.trust.models import LeagueFormatScan

TRUST_MODIFIER_FULL_SUPPORT    = 1.00
TRUST_MODIFIER_PARTIAL_SUPPORT = 0.75
TRUST_MODIFIER_UNSUPPORTED     = 0.50

def compute_trust_modifier(scan: LeagueFormatScan, acknowledged: bool) -> float:
    if scan.league_unsupported:
        return TRUST_MODIFIER_UNSUPPORTED
    if scan.needs_acknowledgment and not acknowledged:
        return TRUST_MODIFIER_PARTIAL_SUPPORT
    if scan.needs_acknowledgment and acknowledged:
        # User has seen the warning; apply lighter degradation
        return TRUST_MODIFIER_PARTIAL_SUPPORT
    return TRUST_MODIFIER_FULL_SUPPORT
```

**Important:** The trust modifier dampens displayed confidence but does NOT suppress recommendations. The tool should still surface direction labels and trade suggestions — it just reduces the confidence band from High to Medium, or Medium to Low, and annotates outputs with the relevant warning.

### Pattern 6: Warning Banner (Frontend)

Follow the `ConcentrationAlertBanner.tsx` pattern exactly:
- Use shadcn `Alert` component with `AlertTriangle` icon (already used in `ConcentrationAlertBanner`)
- Show one banner per affected rule category (partially supported / unsupported)
- For partially supported rules: show banner + "I understand, continue" button that triggers the acknowledgment POST
- For unsupported rules: show persistent non-dismissible banner — acknowledgment is not offered, just disclosure
- Render the banner at the top of the league detail page (`league.$leagueId.tsx`), above existing content panels
- Query banner visibility from `/trust/{league_id}/scan` on page load via TanStack Query

**Dismissible vs non-dismissible:**
- `partially_supported` rules: dismissible (user can acknowledge)
- `unsupported` rules: non-dismissible (persistent) — the tool explicitly warns that advice may be wrong

### Pattern 7: `/trust` Router

New FastAPI router at `backend/src/fantasy/routers/trust.py`:
```
GET  /trust/{league_id}/scan         → LeagueFormatScan (runs scanner on stored settings)
POST /trust/{league_id}/acknowledge  → stores acknowledgment
GET  /trust/{league_id}/acknowledged → returns current acknowledgment state
```

All three endpoints follow the `deps.get_read_db_conn` / `get_write_db_conn` pattern already used by `leagues.py` and `intelligence.py`.

### Recommended Project Structure

New module: `backend/src/fantasy/trust/`

```
backend/src/fantasy/trust/
├── __init__.py
├── constants.py        # FormatRule enum, RULE_SUPPORT_MATRIX, trust modifier constants
├── models.py           # RuleScanEntry, LeagueFormatScan, FormatAcknowledgment
├── scanner.py          # scan_league_format() pure function
├── confidence.py       # compute_trust_modifier()
└── trust_repo.py       # DuckDB upsert/select for acknowledgment table
```

New router: `backend/src/fantasy/routers/trust.py`

Migration: `backend/alembic/versions/015_trust_infrastructure.py`

Frontend: `frontend/src/components/FormatWarningBanner.tsx`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Scoring_settings key enumeration | Custom parser that reads Sleeper docs | Read from actual `scoring_settings` dict via key presence + non-zero value checks |
| Devy detection | Custom devy player registry | Check `years_exp < 0` on rostered player records from existing `players` table |
| Session-level acknowledgment | Cookie/localStorage-based ack state | DuckDB `league_format_acknowledgments` table (same pattern as `league_taxi_configs`) |
| Per-engine confidence injection | Modifying each engine's internals | Apply trust_modifier at the router/API response layer before returning |
| Warning banner from scratch | Custom modal/dialog | shadcn `Alert` component — follow `ConcentrationAlertBanner.tsx` exactly |
| Enum serialization | Custom JSON coercers | Pydantic v2 handles `StrEnum` serialization to string automatically |

---

## Common Pitfalls

### Pitfall 1: Treating missing scoring_settings keys as "not using that scoring"

**Problem:** Sleeper omits scoring keys that have value 0.0. A league with no first-down scoring will have `rush_fd` absent from `scoring_settings`, not present with value 0. Checking `ss.get("rush_fd", 0.0) == 0.0` covers both cases correctly.

**Prevention:** Always use `.get(key, 0.0)` — never `key in ss` as the only check. Apply the same logic to `settings_blob` integer flags: `sb.get("best_ball", 0)`.

### Pitfall 2: Checking `salary_cap` key to detect FAAB leagues

**Problem:** `waiver_budget` (FAAB) is completely separate from salary cap (contract) leagues. Both connected leagues have `waiver_budget: 200` but `salary_cap: 0`. Using `waiver_budget > 0` as a salary cap signal produces false positives for every FAAB league.

**Prevention:** Only use `settings.settings_blob.get("salary_cap", 0)` for contract/salary league detection.

### Pitfall 3: Invalidating acknowledgments too aggressively

**Problem:** If the scanner re-runs on every ingest and any scoring_settings float drift (rounding changes) causes a "different" scan result, users must re-acknowledge constantly.

**Prevention:** Compare rule sets by `frozenset` of `FormatRule` strings, not by full scan object equality. Only invalidate if the set of rule identifiers changes (a new rule appears or an existing rule disappears).

### Pitfall 4: Suppressing recommendations for unsupported leagues

**Problem:** Completely hiding direction labels and trade advice for IDP or devy leagues makes the tool useless even for format-agnostic decisions.

**Prevention:** Never suppress. Always show advice with the unsupported-format banner. Reduce confidence band displayed; never remove the output.

### Pitfall 5: Schema triple-write gap (existing blocker, STATE.md)

**Problem:** STATE.md documents that new tables must be added in three places: Alembic migration, `startup_tasks.py` `_SCHEMA_COMPAT_TABLES`, and `conftest.py`. Missing any one causes silent failures.

**Prevention:** The `league_format_acknowledgments` table MUST appear in all three. This is the only pattern used in the project and must be followed exactly.

### Pitfall 6: Devy detection via player records requires populated players table

**Problem:** Devy detection from `years_exp < 0` requires that rostered players are present in the `players` table with their `years_exp` metadata. If the players table is stale, devy detection silently misses.

**Prevention:** Devy detection is LOW confidence without fresh player data. Flag this as a "best-effort" detection and document it in the banner reason text. Do not block on it.

### Pitfall 7: `league_average_match` is ALREADY active in both connected leagues

**Problem:** Both real leagues have `league_average_match=1` and currently receive unwarned high-confidence advice. Phase 14 will cause warnings to appear on first load after deployment.

**Prevention:** This is the correct behavior — the warnings should appear. Ensure that the "I understand, continue" acknowledgment is available for median wins (a partially supported, not unsupported, rule). The user can dismiss it per league.

---

## Validation Architecture

### What acceptance tests must verify

**Backend unit tests** (`backend/tests/test_trust_scanner.py`):

1. `scan_league_format` with standard dynasty half-PPR superflex TEP settings → emits `HALF_PPR`, `SUPERFLEX`, `TEP` as supported; no partially_supported or unsupported entries; `needs_acknowledgment=False`, `league_unsupported=False`.

2. `scan_league_format` with `league_average_match=1` → emits `MEDIAN_WINS` as `partially_supported`, `distorts_recommendations=True`; `needs_acknowledgment=True`.

3. `scan_league_format` with `best_ball=1` → emits `BEST_BALL` as `unsupported`; `league_unsupported=True`.

4. `scan_league_format` with `salary_cap=1` → emits `SALARY_CAP` as `unsupported`.

5. `scan_league_format` with `DL`, `LB`, `DB` in `roster_positions` → emits `IDP` as `unsupported`.

6. `scan_league_format` with `rush_fd=1.0` in `scoring_settings` → emits `FIRST_DOWN_SCORING` as `partially_supported`.

7. `scan_league_format` with `type=0` (redraft) → emits `NON_DYNASTY` as `unsupported`.

8. `scan_league_format` with `waiver_budget=200, salary_cap=0` → does NOT emit `SALARY_CAP`.

9. `compute_trust_modifier` with full-support scan → returns `1.00`.

10. `compute_trust_modifier` with partially supported scan, unacknowledged → returns `0.75`.

11. `compute_trust_modifier` with unsupported scan → returns `0.50`.

**Backend integration tests** (`backend/tests/test_trust_router.py`):

12. `GET /trust/{league_id}/scan` → returns `LeagueFormatScan` with correct entries for both real leagues (which have `league_average_match=1`).

13. `POST /trust/{league_id}/acknowledge` → persists acknowledgment; subsequent `GET /trust/{league_id}/acknowledged` confirms acknowledged state.

14. After re-ingest with changed settings (simulated by updating settings_blob directly in test DB), acknowledgment is cleared.

**Frontend acceptance criteria** (manual or Playwright):

15. League detail page for either real league shows the median-wins warning banner above the panel stack.

16. Clicking "I understand, continue" dismisses the banner for the session and persists across page reload.

17. An `unsupported` rule banner (if triggered) does not show a dismiss button.

18. Warning banner does not appear for a league with no flagged rules.

**Success criteria crosswalk:**

| Roadmap criterion | How validated |
|------------------|--------------|
| Scanner flags IDP, devy, salary cap, contracts, best ball, empire, median wins, points per first down, return-yard scoring, TE-premium variants | Tests 1–8 above cover all except empire (manual-only) and devy (best-effort note) |
| Each rule classified as supported/partially supported/unsupported | Test 1–8; check entry `support_level` values |
| Partially supported requires manual acknowledgment where recs may be distorted | Tests 12–13; frontend test 15–16 |
| League-level warning banner when rule set outside trusted support matrix | Frontend tests 15–18 |
| Fallback behavior defined and applied for every partially supported rule | Tests 9–11 verify trust_modifier; review that all partially_supported entries have `distorts_recommendations` flag |

---

## Confidence Levels Summary

| Finding | Confidence | Source |
|---------|-----------|--------|
| `settings_blob` keys (best_ball, league_average_match, salary_cap, type, taxi_*) | HIGH | Live Sleeper API call against connected leagues |
| `scoring_settings` key names (rec, bonus_rec_te, rush_fd, rec_fd, pass_fd, ret_yd, kr_td) | HIGH (rec, bonus_rec_te observed); MEDIUM (fd/ret keys inferred from community docs, absent in connected leagues) | Live DB + community sources |
| IDP roster_positions strings (DL, LB, DB, IDP_FLEX, EDGE, CB, S) | MEDIUM | Community tools + Sleeper support docs; not observed in connected leagues |
| Devy detection via `years_exp < 0` | LOW | Inferred from player data model; no Sleeper docs confirm this |
| Empire format — not detectable via API | MEDIUM | Sleeper docs do not document empire; treated as out of scope for automated detection |
| `salary_cap` != FAAB (`waiver_budget`) | HIGH | Directly confirmed by inspecting both connected leagues |
| Schema triple-write requirement | HIGH | STATE.md blocker note; verified in startup_tasks.py |
| Acknowledgment persistence in DuckDB vs session | HIGH | Consistent with existing per-league config patterns (taxi_config, draft_order_rules) |
| `trust_modifier` at response layer (not engine internals) | HIGH (design decision) | Consistent with existing confidence band display in `confidence_band` fields |

---

## Sources

- [Sleeper API documentation](https://docs.sleeper.com/) — official but sparse on field details
- [Sleeper Support: League Types & Formats](https://support.sleeper.com/en/articles/3537396-league-types-formats)
- [Sleeper Support: Extra Game Against League Median](https://support.sleeper.com/en/articles/3971690-extra-game-each-week-against-league-median)
- [Sleeper Support: What Scoring Options Are Available](https://support.sleeper.com/en/articles/3998131-what-scoring-options-are-available)
- [ffscrapr Sleeper basics](https://ffscrapr.ffverse.com/articles/sleeper_basics.html) — confirms `best_ball`, `salary_cap`, `idp` boolean flags in settings
- Live DuckDB inspection of `/Users/jakyeamos/Desktop/Fantasy/data/fantasy.duckdb` — all settings_blob and scoring_settings observations are direct reads from real league data
- Live Sleeper API call to `https://api.sleeper.app/v1/league/1312124666680180736` — confirmed full settings object structure
