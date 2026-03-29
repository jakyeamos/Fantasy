# Phase 13: Context Awareness — Research

**Phase goal:** Recommendations change intentionally with the dynasty calendar and react to football
reality shifts — calendar state and NFL context freshness are explicit, visible, and attributable.

**Requirements addressed:** FS-03 (Dynasty Calendar Mode), FS-08 (NFL Context Freshness)

**Research date:** 2026-03-26

---

## User Constraints

No CONTEXT.md exists for Phase 13. The phase is constrained by the requirements defined in
FANTASY-BACKLOG.md (FS-03, FS-08) and the ROADMAP.md success criteria.

**Locked decisions from prior phases (immutable):**
- Python 3.12 / FastAPI / DuckDB 1.5.0 / Polars backend
- Alembic migrations numbered sequentially; next migration is **015** (014 is the last)
- Triple-write schema discipline: every new table must appear in Alembic migration, `startup_tasks.py`
  `_SCHEMA_COMPAT_TABLES`, and `conftest.py` SCHEMA_SQL
- Pydantic v2 models with `ConfigDict(frozen=False)` — no dataclasses for domain models
- Constants live in `constants.py` files per package; no magic numbers in engine code
- `Literal`-based string enums for all API-contract type labels (not plain str)
- React 19 / Vite / TanStack Query / shadcn-ui frontend

**Phase 12 dependency:** Phase 13 depends on Phase 12 completing. Migration 015 is reserved for
Phase 12 (rookie_pick tables). Phase 13 starts at migration 016.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `freezegun` | 1.5.1 (latest as of 2026-03) | Freeze `datetime.now()` in tests | Mature ecosystem, pytest integration via `@freeze_time`, widely used for time-rule testing |
| `python-dateutil` | 2.9.0 (already installed) | Date arithmetic, relativedelta for calendar math | Standard stdlib extension; already present in environment |

**Installation:**
```bash
pip install freezegun
```

Add to `pyproject.toml` dev dependencies:
```toml
[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "pytest-httpx>=0.30",
  "freezegun>=1.5",  # ADD
]
```

**Version verification:** `npm view` is not applicable; use `pip index versions freezegun`.
`freezegun` 1.5.x is the current stable branch. `time-machine` (C-extension alternative, 10–100x
faster) is an option if test suite performance becomes a concern, but freezegun is sufficient for
this project's test volume and has no C-build requirements.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `time-machine` | 2.x | Faster C-extension time freezing | Only if freezegun shows CI slowness (>2s overhead per test); not needed now |
| `python-dateutil` | 2.9.0 | `relativedelta`, `rrule` for complex date offsets | Use for "third Monday of the month" style NFL event approximations |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `freezegun` | `unittest.mock.patch('datetime.datetime')` | freezegun patches all datetime consumers atomically; manual patching misses third-party modules |
| `freezegun` | `time-machine` | time-machine is faster but adds C build dependency; not worth it for this test volume |
| Hardcoded date ranges | `python-dateutil` rrule | rrule computes recurring events correctly but is overkill for annual NFL events; a named constant dict of (month, day) ranges is simpler and more readable |

---

## Architecture Patterns

### Recommended Package Structure

```
backend/src/fantasy/
├── context/
│   ├── __init__.py
│   ├── constants.py          # CalendarState enum, CALENDAR_WINDOWS, FRESHNESS_DOMAINS, NFL_KEY_EVENTS
│   ├── models.py             # CalendarContext, FreshnessTag, FreshnessReport Pydantic models
│   ├── calendar_service.py   # CalendarService: auto-detect + manual override logic
│   ├── freshness_service.py  # FreshnessService: domain staleness computation + event triggers
│   └── context_repo.py       # DuckDB persistence for manual override + freshness timestamps
└── routers/
    └── context.py            # GET /context/calendar, POST /context/calendar/override, GET /context/freshness
```

### Pattern 1: Dependency-Injected Clock

**What:** Pass `now: Callable[[], datetime]` into CalendarService and FreshnessService constructors
rather than calling `datetime.now()` directly. Tests inject a fixed callable; production passes
`datetime.datetime.now`.

**When to use:** Every function that branches on the current date. This is the single most important
architectural discipline for this phase — it makes every calendar decision unit-testable without
patching.

**Example:**
```python
# context/calendar_service.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Callable

from fantasy.context.constants import CalendarState, CALENDAR_WINDOWS
from fantasy.context.context_repo import ContextRepo

ClockFn = Callable[[], datetime]


class CalendarService:
    def __init__(
        self,
        repo: ContextRepo,
        now: ClockFn = lambda: datetime.now(tz=timezone.utc),
    ) -> None:
        self._repo = repo
        self._now = now

    def active_state(self, league_id: str) -> CalendarState:
        override = self._repo.get_override(league_id)
        if override is not None:
            return override
        return _detect_state(self._now())
```

```python
# In tests
from freezegun import freeze_time

@freeze_time("2026-04-24")  # NFL Draft week
def test_draft_state():
    service = CalendarService(repo=FakeRepo())
    assert service.active_state("league_x") == CalendarState.POST_NFL_DRAFT
```

### Pattern 2: CalendarState Enum with Date-Range Detection

**What:** A `CalendarState` Literal enum with 8 named dynasty phases. A detection function maps
`(month, day)` to a state using ordered ranges defined in a constants dict. Ranges are approximate
and intentionally loose — the goal is dynasty-relevant context, not strict NFL scheduling.

**When to use:** Auto-detection path (no manual override). The date ranges should be defined as
constants, not magic numbers in engine code.

**Dynasty Calendar States (8 phases, HIGH confidence — confirmed against industry sources and
FS-03):**

| State | Approximate Window | Dynasty Significance |
|---|---|---|
| `startup` | Any time (manual only) | Startup draft in progress; high pick demand |
| `preseason` | July 15 – Aug 28 | Training camp; veterans discounted, camp darlings peak |
| `early_season` | Aug 29 – Oct 31 | Season starts; picks cheapest; contenders emerge |
| `trade_deadline` | Nov 1 – Nov 21 | Deadline pressure; rebuilders selling; contenders buying |
| `playoffs` | Nov 22 – Jan 12 | Fantasy playoffs; title-push trades; sit-wait dynamic |
| `rookie_fever` | Jan 13 – Apr 22 | Post-season through pre-draft; pick premium highest; Feb–Apr peak |
| `post_combine` | Feb 24 – Mar 10 | Combine data in; prospect values shift; free agency begins |
| `post_nfl_draft` | Apr 23 – May 15 | Draft week + rookie landing spots; class values settle |

**Key dates verified for 2026:**
- NFL Free Agency opens: March 11, 2026
- NFL Combine: February 23 – March 2, 2026
- NFL Draft: April 23–25, 2026 (Pittsburgh)
- Fantasy rookie drafts: typically May–July (league-dependent; not hardcoded)

**Important:** `post_combine` and `rookie_fever` overlap in late February–early March. Use
`post_combine` during the overlap window (more specific). `startup` is never auto-detected — it
requires a manual override, because the tool cannot know if a league is in startup.

**Example:**
```python
# context/constants.py
from __future__ import annotations
from typing import Literal

CalendarState = Literal[
    "startup",
    "preseason",
    "early_season",
    "trade_deadline",
    "playoffs",
    "rookie_fever",
    "post_combine",
    "post_nfl_draft",
]

# (month, day) inclusive ranges — ordered from most specific to least
# Each entry: (start_month, start_day, end_month, end_day, state)
# Evaluated in order; first match wins
CALENDAR_WINDOWS: list[tuple[int, int, int, int, str]] = [
    (4, 23, 5, 15, "post_nfl_draft"),   # draft week + landing spots settling
    (2, 24, 3, 10, "post_combine"),     # combine through early free agency
    (1, 13, 4, 22, "rookie_fever"),     # post-playoffs through pre-draft
    (11, 22, 1, 12, "playoffs"),        # dynasty fantasy playoffs
    (11, 1, 11, 21, "trade_deadline"),  # trade deadline pressure window
    (7, 15, 8, 28, "preseason"),        # training camp through week before season
    (8, 29, 10, 31, "early_season"),    # week 1 through mid-season
]
# Fallback if no window matches: "early_season"
FALLBACK_STATE: str = "early_season"
```

### Pattern 3: FreshnessTag on Recommendation Outputs

**What:** A `FreshnessTag` Pydantic model attached to recommendation surfaces. It carries the
domain name, last-updated timestamp, whether it is stale, and a human-readable warning string.
Engines read their relevant domains from FreshnessService and attach the tag to output — they do
not compute staleness themselves.

**When to use:** Any recommendation surface that depends on football-reality data that can become
stale between ingest runs (injuries, depth charts, free agency, draft capital, landing spots).

**Freshness Domains (FS-08):**

| Domain | Staleness Threshold | Source |
|---|---|---|
| `injuries` | 48 hours | Sleeper ingest (auto) |
| `depth_chart` | 7 days | Sleeper/nfl_data_py (auto) |
| `free_agency` | 72 hours during open window; 14 days otherwise | Manual flag + ingest |
| `combine` | N/A outside combine window; 1 day during | Manual/nfl_data_py |
| `draft_capital` | 24 hours during draft; 30 days otherwise | Manual/nfl_data_py |
| `landing_spots` | 7 days during/after draft | Manual override path |

**Example model:**
```python
# context/models.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FreshnessTag(BaseModel):
    model_config = ConfigDict(frozen=False)

    domain: str                   # e.g. "injuries", "depth_chart"
    last_updated: datetime | None
    is_stale: bool
    warning: str | None = None    # e.g. "Injury data is 3 days old — verify before trading"


class CalendarContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    active_state: str             # CalendarState literal
    is_override: bool             # True if manual, False if auto-detected
    override_set_by: str | None   # "user" or None
    detected_at: datetime


class RecommendationContext(BaseModel):
    """Attached to any recommendation surface output that needs context attribution."""
    model_config = ConfigDict(frozen=False)

    calendar_state: str
    freshness_tags: list[FreshnessTag] = []
    calendar_note: str | None = None   # human-readable state rationale
```

### Pattern 4: Context Decorator for Existing Engines (Wrapping, Not Rewriting)

**What:** Rather than refactoring every existing engine to accept calendar state, a thin
`ContextEnricher` class reads the active `CalendarContext` and `FreshnessReport` and attaches
them to existing output models that already have a `computation_json` field. For new outputs
(calendar-state-varied guidance text), engines accept a `CalendarContext` argument with a
`None`-safe default.

**When to use:** Attaching calendar/freshness tags to existing engine outputs without touching
the engine's core computation. Add a `context: CalendarContext | None = None` parameter to
engine call signatures; engines that do not yet consume context simply pass it through to
the output wrapper.

**Anti-pattern to avoid:** Do not embed calendar-state logic inside `ScorecardEngine`,
`DirectionEngine`, or `LineupEngine`. Calendar awareness belongs in a dedicated service layer.
The engines produce their outputs; the context layer annotates them.

### Pattern 5: Calendar-State-Varied Guidance Text via Template Dict

**What:** Calendar-state-specific guidance text is defined as a constants dict mapping
`(CalendarState, guidance_type)` to template strings. Engines look up their relevant key;
they never branch on `if state == "rookie_fever"` inline.

**When to use:** Anywhere recommendation text should change across calendar windows.
Trade engine timing_quality reasoning, pick timing reasoning, dashboard headline copy.

**Example:**
```python
# context/constants.py
CALENDAR_GUIDANCE: dict[tuple[str, str], str] = {
    ("rookie_fever", "pick_sell"):
        "Peak rookie fever window — selling now maximizes return before draft inflates competition",
    ("rookie_fever", "pick_hold"):
        "Already in the peak window — if holding, do so only with strong conviction on class quality",
    ("post_nfl_draft", "pick_sell"):
        "Post-draft: prospect values are settling — sell within 2 weeks before landing-spot hype fades",
    ("trade_deadline", "veteran_sell"):
        "Trade deadline window — teams in win-now mode are paying premium for proven starters",
    ("playoffs", "veteran_sell"):
        "Playoff push — contenders paying above-market for short-term help; capitalize if rebuilding",
    ("preseason", "veteran_buy"):
        "Camp darling risk: veterans being replaced by hype are being discounted; buying window",
    ("early_season", "pick_buy"):
        "Early season — pick prices are at annual lows; best time to acquire future firsts",
}
```

### Anti-Patterns to Avoid

- **Hardcoding absolute dates as literals in engine code:** `if month == 4 and day > 23` in
  `trade_engine.py`. Put all date ranges in `context/constants.py`.
- **Coupling every engine to CalendarService:** Engines receive a `CalendarContext` value object,
  not a service reference. Services are only called at the router/orchestration layer.
- **Treating `startup` as auto-detectable:** It is a manual-only state because the tool cannot
  know from the date alone that a league is in its startup draft.
- **Single staleness threshold for all contexts:** Injury freshness during the NFL Draft weekend
  matters more than in February. Domain thresholds must be calendar-state-aware (vary per domain).
- **Writing freshness warnings for every recommendation:** Only freshness-sensitive surfaces get
  tags. The test: "would stale data in this domain meaningfully change this recommendation?"

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test-time date freezing | `monkeypatch.setattr(datetime, 'now', ...)` | `freezegun` `@freeze_time` decorator | monkeypatch misses C-ext datetime callers; freezegun patches all consumers atomically |
| Date arithmetic across month/year boundaries | Manual `timedelta` math | `python-dateutil` `relativedelta` | Edge cases: leap years, month-end rollovers, DST — dateutil handles all of these |
| State machine library for 8 calendar states | `python-statemachine`, `transitions` | Plain `Literal` enum + detection function | 8 states with fixed annual transitions is too simple to justify a state machine dependency; linear ordered-range lookup is sufficient |
| Cron/scheduler for event triggers | `APScheduler`, `Celery` | Manual `POST /context/refresh` endpoint + ingest hook | This is a personal local tool; there is no production job queue; event triggers are user-initiated or ingest-hook-driven |

**Key insight:** Dynasty calendar state is a lookup table problem, not a state machine problem.
The NFL calendar follows a fixed annual pattern; there are no runtime transitions between states
triggered by domain events. A simple ordered-range detection function with a manual override
table is the correct solution. Using a state machine framework would add dependency weight and
testing surface for no benefit.

---

## Common Pitfalls

### Pitfall 1: NFL Calendar Dates Shift Year to Year (HIGH confidence)
The NFL Draft date, combine dates, trade deadline, and season start vary by 2–7 days each year.
**Do not hardcode `month=4, day=24` as "draft starts."** Define windows as `(month, day)` ranges
with meaningful slack (e.g., April 20–May 10 for `post_nfl_draft`). The current year's exact
dates can be manually confirmed and stored in the constants dict per season if precision matters.

**Mitigation:** Use 10–15 day windows for each state. Document that constants require annual
review. Add a `# ANNUAL REVIEW: verify against nfl.com/operations/nfl-schedule/` comment on
the `CALENDAR_WINDOWS` constant.

### Pitfall 2: Timezone Ambiguity in Calendar Detection (HIGH confidence)
NFL events are Eastern Time. A user in a different timezone checking the app at 11 PM PT on
April 22 (draft day -1) gets different behavior than a user at 2 AM ET April 23 (draft day).
**Mitigation:** Normalize all calendar detection to UTC. Document that window boundaries are
approximate — a ±24-hour tolerance is acceptable for dynasty calendar purposes.

### Pitfall 3: Stale Override Divergence (MEDIUM confidence)
A manual `startup` override set in January can persist silently into March, causing all
recommendations to behave as if the user is in a startup draft. **Mitigation:** Manual overrides
must have an expiry TTL stored in the DB (e.g., 30 days). Surface the active override + set date
prominently in the UI. Include a "clear override" CTA.

### Pitfall 4: Freshness Tags on Every Output Increases Noise (MEDIUM confidence)
If every recommendation shows a freshness warning, users will start ignoring them (alert fatigue).
**Mitigation:** Only tag outputs when `is_stale=True`. Do not show a freshness tag when data is
fresh. The absence of a tag is the signal that data is current.

### Pitfall 5: `post_combine` and `rookie_fever` Overlap (HIGH confidence — known domain issue)
The combine (late February) falls inside the rookie fever window (January–April). Having two
active states creates ambiguity. **Mitigation:** Ordered-range lookup with `post_combine` as
higher priority than `rookie_fever`. After the combine ends (≈ March 10), the state naturally
falls back to `rookie_fever`.

### Pitfall 6: Calendar State Does Not Affect Pick Engine's Existing Month Multiplier (HIGH confidence)
`picks/constants.py` already has `CALENDAR_TIMING_MULTIPLIERS: dict[int, float]` — a month-to-
multiplier table. Phase 13 should not replace this with a calendar-state multiplier; the pick
engine already handles calendar-aware pick valuation at a different granularity. Phase 13 adds
higher-level guidance *text* and freshness metadata on top. Avoid duplication.

### Pitfall 7: Schema Triple-Write Discipline Required (HIGH confidence — project-specific)
Any new DuckDB tables (`calendar_overrides`, `freshness_domains`) must appear in three places:
Alembic migration (016), `startup_tasks.py` `_SCHEMA_COMPAT_TABLES`, and `conftest.py`
`SCHEMA_SQL`. Failing to add any one location causes silent test failures or startup failures.
This is documented as a known blocker in STATE.md.

---

## Validation Architecture

### How to Verify Phase 13 Works End-to-End

**Test Strategy: freezegun fixtures for each calendar state**

The primary verification mechanism is a parameterized test that freezes time to a representative
date in each of the 8 calendar states and asserts that:
1. `CalendarService.active_state()` returns the correct `CalendarState`
2. Recommendation text for a fixed asset contains a substring from that state's guidance template
3. The output model carries a `calendar_state` field equal to the detected state

```python
# tests/context/test_calendar_service.py
import pytest
from freezegun import freeze_time
from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import CalendarState

@pytest.mark.parametrize("frozen_date,expected_state", [
    ("2026-04-24", "post_nfl_draft"),    # draft day 2
    ("2026-03-01", "post_combine"),      # combine weekend
    ("2026-02-15", "rookie_fever"),      # pre-combine rookie fever
    ("2026-11-10", "trade_deadline"),    # trade deadline week
    ("2026-12-01", "playoffs"),          # fantasy playoffs
    ("2026-08-01", "preseason"),         # training camp
    ("2026-09-15", "early_season"),      # week 3 of season
])
@freeze_time
def test_auto_detect_state(frozen_date, expected_state):
    service = CalendarService(repo=FakeContextRepo())
    assert service.active_state("league_x") == expected_state
```

**Test: Same asset, different guidance in different calendar windows**

Success criterion #3 requires a demonstrable behavioral difference. Implement as a test that
calls the pick timing recommendation (or trade timing_quality dimension) with the same inputs
but with calendar state injected as `post_nfl_draft` vs `early_season` and asserts that the
returned guidance text differs.

**Test: Freshness warning surfaces on stale domains**

Write a test that seeds a `freshness_domains` row with `last_updated` set to 3 days ago, freezes
time to "now", and asserts that `FreshnessService.get_tags(["injuries"])` returns
`[FreshnessTag(domain="injuries", is_stale=True, warning=...)]`.

**Test: Manual override suppresses auto-detection**

Seed a `calendar_overrides` row with `state="startup"`, call `CalendarService.active_state()`,
and assert it returns `"startup"` regardless of the frozen date.

**Frontend validation checkpoint:**

After backend is wired, manually verify that:
1. The trade recommendation page shows the calendar state badge (e.g., "Post-NFL Draft")
2. The pick timing recommendation panel's reasoning text includes a calendar-state citation
3. Changing the override via POST and refreshing shows the new state in the UI

### DB Schema for Validation

Two new tables (migration 016):

```sql
-- calendar state manual overrides per league
CREATE TABLE IF NOT EXISTS calendar_overrides (
    id          INTEGER PRIMARY KEY,
    league_id   VARCHAR NOT NULL UNIQUE,
    state       VARCHAR NOT NULL,
    set_by      VARCHAR NOT NULL DEFAULT 'user',
    set_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP
);

-- freshness domain last-updated timestamps per league
CREATE TABLE IF NOT EXISTS freshness_domains (
    id           INTEGER PRIMARY KEY,
    league_id    VARCHAR NOT NULL,
    domain       VARCHAR NOT NULL,
    last_updated TIMESTAMP,
    notes        VARCHAR,
    UNIQUE (league_id, domain)
);
```

---

## Code Examples

### CalendarService: Auto-detect + Override

```python
# backend/src/fantasy/context/calendar_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fantasy.context.constants import (
    CALENDAR_WINDOWS,
    FALLBACK_STATE,
    CalendarState,
)
from fantasy.context.context_repo import ContextRepo
from fantasy.context.models import CalendarContext

ClockFn = Callable[[], datetime]


def _detect_state(now: datetime) -> str:
    month, day = now.month, now.day
    for start_m, start_d, end_m, end_d, state in CALENDAR_WINDOWS:
        if _in_range(month, day, start_m, start_d, end_m, end_d):
            return state
    return FALLBACK_STATE


def _in_range(m: int, d: int, sm: int, sd: int, em: int, ed: int) -> bool:
    # Handles same-year ranges only; wrap-around (playoffs Nov–Jan) handled separately
    if sm <= em:
        if sm < m < em:
            return True
        if m == sm and d >= sd:
            return True
        if m == em and d <= ed:
            return True
    else:
        # Cross-year range (e.g., Nov 22 – Jan 12)
        if m > sm or (m == sm and d >= sd):
            return True
        if m < em or (m == em and d <= ed):
            return True
    return False


class CalendarService:
    def __init__(
        self,
        repo: ContextRepo,
        now: ClockFn = lambda: datetime.now(tz=timezone.utc),
    ) -> None:
        self._repo = repo
        self._now = now

    def active_state(self, league_id: str) -> str:
        override = self._repo.get_override(league_id)
        if override is not None:
            return override
        return _detect_state(self._now())

    def get_context(self, league_id: str) -> CalendarContext:
        override = self._repo.get_override(league_id)
        is_override = override is not None
        state = override if is_override else _detect_state(self._now())
        return CalendarContext(
            active_state=state,
            is_override=is_override,
            override_set_by="user" if is_override else None,
            detected_at=self._now(),
        )
```

### FreshnessService: Domain Staleness Check

```python
# backend/src/fantasy/context/freshness_service.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from fantasy.context.constants import FRESHNESS_THRESHOLDS
from fantasy.context.context_repo import ContextRepo
from fantasy.context.models import FreshnessTag

ClockFn = Callable[[], datetime]


class FreshnessService:
    def __init__(
        self,
        repo: ContextRepo,
        now: ClockFn = lambda: datetime.now(tz=timezone.utc),
    ) -> None:
        self._repo = repo
        self._now = now

    def get_tags(self, league_id: str, domains: list[str]) -> list[FreshnessTag]:
        rows = self._repo.get_freshness_rows(league_id, domains)
        now = self._now()
        tags: list[FreshnessTag] = []
        for domain in domains:
            row = rows.get(domain)
            threshold_hours = FRESHNESS_THRESHOLDS.get(domain, 48)
            if row is None or row.last_updated is None:
                tags.append(FreshnessTag(
                    domain=domain,
                    last_updated=None,
                    is_stale=True,
                    warning=f"{domain.replace('_', ' ').title()} data has never been updated — verify before acting",
                ))
                continue
            age = now - row.last_updated.replace(tzinfo=timezone.utc)
            is_stale = age > timedelta(hours=threshold_hours)
            warning = (
                f"{domain.replace('_', ' ').title()} data is {int(age.total_seconds() / 3600)}h old"
                if is_stale else None
            )
            tags.append(FreshnessTag(
                domain=domain,
                last_updated=row.last_updated,
                is_stale=is_stale,
                warning=warning,
            ))
        return tags
```

### Recommendation Context Attachment Pattern

```python
# In any engine output that needs context annotation (e.g., trade router)
from fantasy.context.models import RecommendationContext

def build_recommendation_context(
    calendar_service: CalendarService,
    freshness_service: FreshnessService,
    league_id: str,
    freshness_domains: list[str],
) -> RecommendationContext:
    ctx = calendar_service.get_context(league_id)
    tags = freshness_service.get_tags(league_id, freshness_domains)
    note = CALENDAR_GUIDANCE.get((ctx.active_state, "general"))
    return RecommendationContext(
        calendar_state=ctx.active_state,
        freshness_tags=tags,
        calendar_note=note,
    )
```

### freezegun Test Pattern

```python
# Standard pattern for all Phase 13 tests
from freezegun import freeze_time

@freeze_time("2026-04-24 12:00:00")
def test_post_nfl_draft_state():
    service = CalendarService(repo=FakeContextRepo())
    ctx = service.get_context("league_x")
    assert ctx.active_state == "post_nfl_draft"
    assert ctx.is_override is False
```

---

## NFL Key Events Reference (2026)

Verified dates for hardening constants before Phase 13 execution:

| Event | Date(s) | Dynasty Impact |
|---|---|---|
| Super Bowl LX | February 8, 2026 | Post-season; rookie fever begins |
| NFL Combine | Feb 23 – Mar 2, 2026 | Prospect values shift; `post_combine` window |
| Free Agency opens | March 11, 2026 | Landing spots begin to clarify |
| Annual League Meeting | March 29 – April 1, 2026 | Rule changes; team context shifts |
| NFL Draft | April 23–25, 2026 (Pittsburgh) | `post_nfl_draft` window; Rd 1 April 23, 8 PM ET |
| Fantasy rookie drafts | League-dependent (May–July) | `rookie_fever` tail; not hardcoded |
| NFL season start (est.) | ~September 3, 2026 | `early_season` begins |
| Trade deadline (est.) | ~Week 11, November 12, 2026 | `trade_deadline` window |

**Sources:** NFL Football Operations official dates page (operations.nfl.com), CBS Sports 2026
offseason calendar, NFL.com 2026 Draft announcement.

---

## Confidence Summary

| Finding | Confidence | Basis |
|---|---|---|
| freezegun is the correct test library for this pattern | HIGH | Multiple official sources, widely used, no C-build deps |
| Dependency-injected clock (ClockFn) is the right architecture | HIGH | hakibenita.com authoritative Python DI article; matches project's own injectable pattern in pick_engine |
| 8 named dynasty calendar states are domain-standard | HIGH | Confirmed against FS-03 backlog + industry sources (DynastyNerds, Apex, industry calendar articles) |
| NFL calendar dates verified for 2026 | HIGH | NFL Football Operations official page |
| `startup` must be manual-only | HIGH | Cannot infer from date alone; FS-03 explicitly states "allows manual override" |
| `post_combine` overlaps `rookie_fever` — ordered-range lookup handles it | HIGH | Domain logic verified against NFL calendar |
| Do not replace existing `CALENDAR_TIMING_MULTIPLIERS` in pick_engine | HIGH | Already exists; Phase 13 adds a layer above it, not a replacement |
| Schema triple-write is required for any new tables | HIGH | Documented in STATE.md as an active known blocker |
| `time-machine` would be faster but is unnecessary here | MEDIUM | Better Stack comparison article; test suite size does not justify C-extension dependency |
| Fantasy rookie draft timing (May–July) is league-dependent | MEDIUM | Industry sources show default dates but leagues can move them |
