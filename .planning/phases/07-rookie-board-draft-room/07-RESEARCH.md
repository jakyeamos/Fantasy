# Phase 7: Rookie Board & Draft Room — Research

**Researched:** 2026-03-22
**Domain:** Dynasty rookie evaluation, tiered ranking systems, draft tendency analysis, FastAPI engine patterns, TanStack Router nested routes, DuckDB analytical patterns
**Confidence:** HIGH (stack and architecture — extends verified Phase 2/4/5/6 patterns), MEDIUM (tier assignment methodology — dynasty community methodology, no single authoritative quantitative standard), MEDIUM (draft tendency derivation — approach is novel to this tool, qualitative community support exists), LOW (class strength scoring formula — first quantitative implementation of a concept that dynasty community treats qualitatively)

---

## User Constraints

> Copied verbatim from 07-CONTEXT.md. Planner MUST honor these.

### Locked Decisions

**Rookie board layout (PICK-04)**
- D-01: Tiered card grid — players grouped in visual tier blocks, not a flat ranked list
- D-02: Labeled tier dividers between blocks (e.g., "Tier 1 — Elite", "Tier 2 — Strong Day 2") — explicit break lines, not per-row indicators
- D-03: Always visible inline on each card: name, position, archetype label — no expand or hover required for these three fields
- D-04: Risk band rendered as both a text label ("Low" / "Moderate" / "High") and a color-coded element (badge color or left border tint) — not one or the other

**Roster-fit overlay (PICK-05)**
- D-05: PICK-05 roster-fit filtered board is descoped — dynasty strategy is value accumulation, not positional need filling; a heavy roster-fit rerank would push toward suboptimal positional thinking in flex formats
- D-06: The team/draft-slot dropdown is repurposed to highlight players likely available at a given pick slot, not to apply roster-fit weighting

**Draft room view (PICK-06)**
- D-07: "Best for this roster" question dropped from draft room — same rationale as D-05; reduces to 3 questions: (1) best in abstract, (2) best relative to this league's draft tendencies, (3) trade vs. use the pick
- D-08: Dedicated route (`/draft-room`) — user selects league and pick slot on entry; not a modal or panel launched from the board
- D-09: Trade recommendation is a direct verdict with one-line reasoning ("Trade it — your 1.04 carries more value than any available prospect here"), not a side-by-side comparison view
- D-10: League draft tendency warnings surface both: positional run warnings ("WRs always go early in this league — don't wait") and value gap alerts ("Player X is being drafted 3 spots earlier than his value")

**Entry points and navigation**
- D-11: Rookie board lives inside the league drill-in — accessed per league, not top-level nav; format recalculates for each league's scoring rules
- D-12: Draft room is reached from the league drill-in — not launched from the rookie board itself
- D-13: Phase 6 "Use on the clock" timing rec is a label only — no navigation link into the draft room
- D-14: Each league gets its own board instance — tiers, risk bands, and archetype labels are recalculated per-league scoring format; no shared cross-league board view

### Claude's Discretion

- Exact tier names and count (how many tiers, what they're called)
- Which color tokens map to which risk bands (within existing shadcn CSS variable set)
- How archetype labels are generated and what the label vocabulary is
- How "available at pick slot" is estimated for the draft-slot dropdown
- How league draft tendencies are derived (positional draft frequency, ADP delta vs. system value)
- Pick slot selector UX on draft room entry (input, dropdown, or stepper)

### Deferred Ideas (out of scope — do not plan)

- Roster-fit filtered board (PICK-05) — descoped; user prefers pure value accumulation strategy over positional need filtering in dynasty flex formats
- "Best for this roster" as a draft room question — same rationale; dropped from PICK-06 scope
- Historical rookie class outcome tracking (did Tier 1 picks hit?) — Phase 8/9 retrospective feature
- Cross-league rookie board comparison (same player, different format adjustments side by side) — future phase

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PICK-04 | System generates a format-aware rookie board with tiers, archetype labels, and risk bands for the current draft class | Tier assignment algorithm documented below; format-awareness via league scoring settings from `leagues` table; archetype label system specified |
| PICK-05 | Descoped per D-05 | Replaced by slot availability highlighting (D-06); no roster-fit computation required |
| PICK-06 | Draft room answers 3 questions: best in abstract, best relative to league draft tendencies, trade vs. use the pick | Three-question architecture documented; trade verdict logic specified; tendency derivation from `league_draft_tendencies` table specified |

---

## Summary

Phase 7 builds two new surfaces (rookie board and draft room) and wires the real `class_strength_signal` into the Phase 6 pick engine. The backend adds a `rookie_board` package with a `RookieEngine` class and a new `league_draft_tendencies` table. The frontend adds two routes: `league.$leagueId.rookie-board.tsx` (nested) and `draft-room.tsx` (standalone). All patterns are extensions of the established Phase 2/4/5/6 engine and router conventions — no new libraries.

The three new computations this phase introduces are:
1. **Class strength scoring**: A composite float (-1.0 to +1.0) computed from the current draft class's prospect profile distribution. Replaces the `0.0` placeholder that Phase 6 has been passing.
2. **Rookie tier and archetype assignment**: Players in the draft class are bucketed into tiers (Tier 1 through Tier 4/5) and labeled with archetype strings based on profile attributes. Risk band (Low/Moderate/High) is a third attribute assigned per player.
3. **League draft tendency analysis**: Positional ADP frequency and value gap detection per league, stored in a new `league_draft_tendencies` table, surfaced as warnings in the draft room.

All three computations are fully deterministic, arithmetic, and re-runnable — same pattern as all prior phases.

---

## Standard Stack

### Core (inherited — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.5.0 | Reads `traded_picks`, `players`, `leagues`, `transactions` tables; writes new `league_draft_tendencies` and `rookie_board_cache` tables | Already locked; all Phase 7 queries are analytical aggregations |
| pydantic | 2.x | Domain models for rookie board engine inputs/outputs | Established pattern across all phases |
| fastapi | 0.115.x | New `/rookie-board` and `/draft-room` routers following Phase 6 picks router pattern | Established pattern |
| polars | 1.x | Bulk aggregation when computing tendency stats across full transaction history | Already in stack |

### Frontend (inherited — one new shadcn component)

| Component | Install Command | Purpose |
|-----------|----------------|---------|
| select | `npx shadcn@latest add select` | Draft room pick slot and league selectors; slot filter on rookie board |

Per 07-UI-SPEC.md, all other components (card, badge, button, separator, skeleton, tabs, table, alert, sheet, input, command, popover, scroll-area) are already installed.

**Version verification:** All packages are installed from prior phases. Only `select` is new.

---

## Architecture Patterns

### Recommended Project Structure Extension

```
backend/src/fantasy/
├── picks/                          # Phase 6 — already exists
│   ├── pick_engine.py              # MODIFIED — class_strength_signal now populated from RookieEngine
│   └── pick_repo.py                # MODIFIED — reads class_strength from rookie_board_cache
├── rookie/                         # NEW — Phase 7 engine
│   ├── __init__.py
│   ├── constants.py                # Tier cutoffs, risk thresholds, archetype label vocabulary
│   ├── models.py                   # RookiePlayer, RookieTier, RookieBoardResult, DraftTendency, DraftRoomResult
│   ├── rookie_engine.py            # RookieEngine — compute_board(), compute_class_strength(), compute_draft_room()
│   └── rookie_repo.py              # DuckDB reads from traded_picks, leagues, transactions; writes to new tables
├── routers/
│   ├── rookie_board.py             # NEW — GET /rookie-board/{league_id}
│   └── draft_room.py               # NEW — GET /draft-room/{league_id}/{pick_slot}

frontend/src/
├── routes/
│   ├── league.$leagueId.rookie-board.tsx   # NEW — nested league route
│   └── draft-room.tsx                       # NEW — standalone route
├── components/rookie/
│   ├── RookiePlayerCard.tsx        # Card with left border risk tint, name/position/archetype/risk badge
│   ├── TierDivider.tsx             # Full-width tier label bar
│   └── TierGroup.tsx               # TierDivider + grid of RookiePlayerCard
├── components/draft-room/
│   ├── VerdictBanner.tsx           # "Trade it" / "Use it" banner following StrategicDistinctionBanner pattern
│   └── TendencyWarningList.tsx     # Alert-based tendency warnings (positional run + value gap)
├── lib/api/
│   ├── rookie-board.ts             # TanStack Query hooks for GET /rookie-board/{league_id}
│   └── draft-room.ts               # TanStack Query hooks for GET /draft-room/{league_id}/{slot}
└── types/
    └── rookie.ts                   # TypeScript types for RookieBoardResponse, DraftRoomResponse
```

### Pattern 1: Engine Class (Same as Phase 2/4/5/6)

```python
# rookie/rookie_engine.py
class RookieEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = RookieRepo(conn)

    def compute_board(self, league_id: str) -> RookieBoardResult:
        """Compute tiered rookie board for a specific league's scoring format."""
        league = self._repo.get_league_settings(league_id)
        picks = self._repo.get_available_rookies(league_id)
        players = [self._score_rookie(p, league) for p in picks]
        players_sorted = sorted(players, key=lambda p: p.composite_score, reverse=True)
        tiers = self._assign_tiers(players_sorted)
        class_strength = self._compute_class_strength(players_sorted)
        return RookieBoardResult(league_id=league_id, tiers=tiers, class_strength_signal=class_strength)

    def compute_class_strength(self, league_id: str) -> float:
        """Returns float in [-1.0, +1.0] for injection into Phase 6 pick engine."""
        board = self.compute_board(league_id)
        return board.class_strength_signal

    def compute_draft_room(self, league_id: str, pick_slot: int) -> DraftRoomResult:
        """Answers 3 questions for the draft room view."""
        board = self.compute_board(league_id)
        tendencies = self._repo.get_league_tendencies(league_id)
        available = self._estimate_available_at_slot(board, pick_slot)
        verdict = self._compute_trade_verdict(league_id, pick_slot, board)
        return DraftRoomResult(
            best_in_abstract=available[0] if available else None,
            tendency_warnings=self._build_tendency_warnings(tendencies, available, pick_slot),
            trade_verdict=verdict,
        )
```

### Pattern 2: Router Registration (Same as Phase 6)

```python
# routers/rookie_board.py
from fastapi import APIRouter, Depends
import duckdb
from fantasy.routers.deps import get_read_db_conn
from fantasy.rookie.rookie_engine import RookieEngine

router = APIRouter(prefix="/rookie-board", tags=["rookie-board"])

@router.get("/{league_id}")
def get_rookie_board(league_id: str, conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn)):
    engine = RookieEngine(conn)
    return engine.compute_board(league_id)
```

```python
# main.py additions
from fantasy.routers import rookie_board, draft_room
app.include_router(rookie_board.router)
app.include_router(draft_room.router)
```

### Pattern 3: Nested Route (Same as `league.$leagueId.managers.tsx`)

```typescript
// frontend/src/routes/league.$leagueId.rookie-board.tsx
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/league/$leagueId/rookie-board")({
  component: RookieBoardPage,
})

function RookieBoardPage() {
  const { leagueId } = Route.useParams()
  // ... uses useQuery(rookieBoardOptions(leagueId))
}
```

### Pattern 4: Standalone Route (Same as `trades.tsx`)

```typescript
// frontend/src/routes/draft-room.tsx
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/draft-room")({
  validateSearch: (search) => ({
    leagueId: search.leagueId as string | undefined,
  }),
  component: DraftRoomPage,
})
```

The `leagueId` query param is passed from the league drill-in "Enter Draft Room" button: `navigate({ to: "/draft-room", search: { leagueId } })`.

### Pattern 5: TanStack Query Hooks (Same as `queries.ts`)

```typescript
// frontend/src/lib/api/rookie-board.ts
export const rookieBoardOptions = (leagueId: string) =>
  queryOptions({
    queryKey: ["rookie-board", leagueId],
    queryFn: () => getJson<RookieBoardResponse>(`/rookie-board/${leagueId}`),
    staleTime: 15 * 60 * 1000,  // 15 minutes — board doesn't change on every load
  })

// frontend/src/lib/api/draft-room.ts
export const draftRoomOptions = (leagueId: string, pickSlot: number) =>
  queryOptions({
    queryKey: ["draft-room", leagueId, pickSlot],
    queryFn: () => getJson<DraftRoomResponse>(`/draft-room/${leagueId}/${pickSlot}`),
    staleTime: 15 * 60 * 1000,
    enabled: !!leagueId && !!pickSlot,
  })
```

### Anti-Patterns to Avoid

- **Per-player API calls on the board:** `GET /rookie-board/{league_id}` returns the entire board in one response, pre-grouped by tier. The response includes `available_probability_by_slot` per player so slot filtering is client-side with no additional fetch.
- **Rebuilding StrategicDistinctionBanner from scratch for VerdictBanner:** VerdictBanner follows the same visual layout as the existing `StrategicDistinctionBanner` component. Read that component before implementing.
- **Hardcoding tier count:** The engine assigns players to tiers dynamically based on score distribution. The number of tiers (4 or 5) depends on whether a 5th "Flier" tier exists. The frontend must handle variable tier counts, not assume exactly 4.
- **Computing class_strength in the frontend:** Class strength is a backend-computed float injected into the Phase 6 pick engine. The frontend renders verdicts verbatim — no client-side class strength logic.
- **Fetching the picks table for league selector in draft room:** The draft room league selector uses the same connected leagues list already available from the dashboard. Do not create a new endpoint for league selection — reuse existing data.

---

## Rookie Board Engine — Research Synthesis

### Component 1: Format-Aware Scoring (CONFIDENCE: HIGH)

Dynasty rookie valuation differs materially by league format. The key format dimensions are already stored in the `leagues` table:
- `ppr` (0.0, 0.5, or 1.0)
- `superflex` (bool)
- `tep` (bool — tight end premium)
- `roster_positions` (JSON — controls lineup slot count by position)

**Scoring adjustments by format:**

| Format Flag | Affected Positions | Adjustment |
|-------------|-------------------|------------|
| `superflex = true` | QB | QB dynasty value increases significantly — best QB prospects move up in tiers |
| `ppr = 1.0` (full PPR) | WR, TE (pass catchers) | Slot receivers and pass-catching RBs gain value; pure runners lose some |
| `ppr = 0.0` (standard) | WR, TE, RB | Rush-heavy backs gain relative value; thin slot WRs lose |
| `tep = true` | TE | TE prospects gain a multiplier — first-round TE caliber moves up |
| Roster positions | All | Positional scarcity in this specific league's lineup affects value |

These flags are already in the database from Phase 1 (INGEST-01). The `RookieEngine` reads them via `RookieRepo.get_league_settings()`. No additional ingestion is needed.

### Component 2: Tier Assignment Algorithm (CONFIDENCE: MEDIUM)

Dynasty community uses tiers as natural breakpoints in a distribution — the space between a tier 1 and tier 2 prospect is larger than within a tier. The algorithm should compute composite scores first, then find natural breakpoints.

**Recommended approach:**

```python
# rookie/rookie_engine.py
def _assign_tiers(self, players: list[RookiePlayer]) -> list[RookieTier]:
    """
    Assign tiers based on composite score gaps.
    Tier boundaries are determined by the score distribution,
    not arbitrary fixed thresholds.
    """
    if not players:
        return []

    scores = [p.composite_score for p in players]

    # Find gaps in score distribution — a gap > GAP_THRESHOLD creates a new tier
    # GAP_THRESHOLD is a named constant in constants.py
    tiers = []
    current_tier_players = [players[0]]
    current_tier_num = 1

    for i in range(1, len(players)):
        gap = scores[i - 1] - scores[i]
        if gap >= GAP_THRESHOLD and current_tier_num < MAX_TIER_COUNT:
            tiers.append(RookieTier(
                tier_number=current_tier_num,
                label=TIER_LABELS[current_tier_num],
                players=current_tier_players,
            ))
            current_tier_players = [players[i]]
            current_tier_num += 1
        else:
            current_tier_players.append(players[i])

    tiers.append(RookieTier(
        tier_number=current_tier_num,
        label=TIER_LABELS[current_tier_num],
        players=current_tier_players,
    ))
    return tiers
```

**Named constants in `rookie/constants.py`:**

```python
GAP_THRESHOLD: float = 8.0        # composite score gap that creates a new tier boundary
MAX_TIER_COUNT: int = 5            # cap at 5 tiers maximum

TIER_LABELS: dict[int, str] = {
    1: "Tier 1 — Elite",
    2: "Tier 2 — Strong Day 2",
    3: "Tier 3 — Day 3 Upside",
    4: "Tier 4 — Developmental",
    5: "Tier 5 — Flier",
}
```

Tier 5 "Flier" only materializes if enough players exist and a gap appears before the 5th tier. The frontend handles variable tier count (1 through 5) without assuming a fixed number.

### Component 3: Archetype Label System (CONFIDENCE: MEDIUM)

Dynasty community uses archetype labels to communicate a player's production profile. Labels are not a free-form field — they come from a controlled vocabulary. The engine assigns labels based on measurable profile attributes.

**Archetype vocabulary by position:**

```python
# rookie/constants.py
ARCHETYPE_LABELS: dict[str, list[str]] = {
    "WR": [
        "Deep Threat",
        "Slot Receiver",
        "Contested Catch WR",
        "Air Raid WR",
        "Big Slot",
        "Route Runner",
        "Possession WR",
    ],
    "RB": [
        "Workhorse",
        "Early Down Back",
        "Third Down Back",
        "Receiving Back",
        "Power Back",
        "Satellite Back",
    ],
    "QB": [
        "Pocket Passer",
        "Dual Threat QB",
        "Scrambler",
        "Pro Style QB",
    ],
    "TE": [
        "Inline Blocker",
        "Move TE",
        "Receiving TE",
        "H-Back",
    ],
}
```

**Assignment logic:** The archetype is derived from profile features available in the `players` table and any prospect scouting data. Since Phase 7 does not yet have Phase 8's historical model, the archetype assignment uses the player's position combined with available metadata (team context, college production profile if available from `player_stats_weekly`, and draft capital slot). A fallback label of `"[Position] Prospect"` is used when data is insufficient for a specific archetype assignment.

**Important:** The archetype label is generated entirely on the backend. The frontend renders verbatim — no client-side archetype computation.

### Component 4: Risk Band Assignment (CONFIDENCE: MEDIUM)

Risk bands (Low / Moderate / High) map to signal patterns known to correlate with dynasty floor and ceiling risk. Three bands are assigned per player.

```python
# rookie/constants.py
RISK_BAND_LOW = "Low"        # Floor-safe: proven role, no injury flag, high college efficiency
RISK_BAND_MODERATE = "Moderate"  # Mixed signals: one concern, no disqualifying factor
RISK_BAND_HIGH = "High"     # Ceiling-only: injury history, role uncertainty, or positional devalue

# Signals that push toward HIGH risk:
# - Injury history (broken bones, ACL, multiple soft tissue)
# - Size concerns for the position
# - Role uncertainty in NFL team context
# - Positional devaluation (pure RBs in PPR-heavy leagues)

# Signals that pull toward LOW risk:
# - Clear depth chart role (signed to starting team, low competition)
# - Efficient college production (high yards/target, market share > 25%)
# - Multiple years of consistent production
# - High draft capital (top 15 NFL pick)
```

Risk band is a synthesis of available signals. Phase 8 will replace this with the backtested historical model. Phase 7's risk band is a best-available signal from current `players` and `player_stats_weekly` data.

### Component 5: Class Strength Signal — Phase 6 Hook Integration (CONFIDENCE: HIGH)

This is the primary integration point between Phase 7 and Phase 6. The `class_strength_signal` field in `PickValuationContext` was set to `0.0` in Phase 6. Phase 7 replaces it.

**The computation:**

```python
# rookie/rookie_engine.py
def _compute_class_strength(self, players: list[RookiePlayer]) -> float:
    """
    Returns float in [-1.0, +1.0].
    Positive = class is historically strong (more Tier 1 talent than baseline).
    Negative = class is historically weak (thinner at top than baseline).
    0.0 = neutral (same as Phase 6 placeholder).
    """
    if not players:
        return 0.0

    tier1_count = sum(1 for p in players if p.tier_number == 1)
    tier2_count = sum(1 for p in players if p.tier_number == 2)

    # Baseline: a "normal" class has BASELINE_TIER1_COUNT Tier 1 players
    # and BASELINE_TIER2_COUNT Tier 2 players
    tier1_delta = tier1_count - BASELINE_TIER1_COUNT
    tier2_delta = tier2_count - BASELINE_TIER2_COUNT

    # Weight tier 1 more heavily than tier 2 in class assessment
    raw_signal = (
        CLASS_TIER1_WEIGHT * tier1_delta / max(BASELINE_TIER1_COUNT, 1)
        + CLASS_TIER2_WEIGHT * tier2_delta / max(BASELINE_TIER2_COUNT, 1)
    )

    # Clamp to [-1.0, 1.0]
    return max(-1.0, min(1.0, raw_signal))
```

**Named constants in `rookie/constants.py`:**

```python
BASELINE_TIER1_COUNT: int = 3     # typical rookie class has ~3 Tier 1 prospects
BASELINE_TIER2_COUNT: int = 5     # typical class has ~5 Tier 2 prospects
CLASS_TIER1_WEIGHT: float = 0.70  # tier 1 depth drives class strength more than tier 2
CLASS_TIER2_WEIGHT: float = 0.30
```

**Integration point:** Phase 7 injects the class strength signal into the existing `PickValuationContext`. The `RookieRepo.get_class_strength(league_id)` method reads from the `rookie_board_cache` table (updated whenever the board is computed). The `PickRepo.get_league_pick_context()` method in Phase 6 is extended to call this getter.

**Critical:** The injection must happen without modifying Phase 6 engine code. The `PickValuationContext.class_strength_signal` field already accepts a float — Phase 7 simply passes a non-zero value. The mechanism is the `PickRepo` reading from the new `rookie_board_cache` table.

### Component 6: Slot Availability Estimation (CONFIDENCE: MEDIUM)

The slot availability feature (D-06) requires estimating whether a player will still be available at a given pick slot. This is a heuristic, not a simulation.

**Recommended approach:**

The `RookieBoardResult` response includes `available_probability_by_slot: dict[str, float]` per player. The backend computes this using a simplified ADP-based probability:

```python
# For a player ranked N-th in their tier, the probability of being
# available at slot S is:
# - If S < N: ~0.0 (someone will take them before you)
# - If S == N: ~0.50 (50% chance they're there at their consensus slot)
# - If S > N: increases as a function of (S - N)

def slot_availability_probability(player_rank: int, slot: int) -> float:
    if slot < player_rank:
        return 0.05  # tiny — very unlikely they fall this far
    gap = slot - player_rank
    # Logistic growth toward certainty as gap increases
    return min(0.95, 0.50 + gap * SLOT_AVAILABILITY_SLOPE)
```

**Named constant:** `SLOT_AVAILABILITY_SLOPE: float = 0.08` — each additional slot beyond consensus rank adds ~8% probability. Named in `rookie/constants.py`.

**Frontend usage:** Per 07-UI-SPEC.md, the frontend uses `AVAILABILITY_THRESHOLD = 0.5` — players with probability >= 0.5 at the selected slot receive the availability highlight. This constant lives in the frontend (not the backend) and is specified in the UI-SPEC.

---

## League Draft Tendency Analysis

### New Table: `league_draft_tendencies` (CONFIDENCE: MEDIUM)

This is a net-new table introduced in Phase 7 to store computed tendency data per league. It feeds the "League Draft Tendencies" answer card in the draft room.

**DDL:**

```sql
-- Alembic migration 008_rookie_board.py
CREATE TABLE IF NOT EXISTS league_draft_tendencies (
    id                      INTEGER PRIMARY KEY,
    league_id               VARCHAR NOT NULL,
    computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tendency_type           VARCHAR NOT NULL,  -- 'positional_run' | 'value_gap'
    position                VARCHAR,           -- e.g. 'WR', 'RB', 'QB', 'TE'
    player_id               VARCHAR,           -- for value_gap entries
    player_name             VARCHAR,           -- denormalized for display
    pick_slot               INTEGER,           -- relevant pick slot
    early_draft_slots       FLOAT,             -- avg slots earlier than system value (positional_run)
    adp_delta               FLOAT,             -- system_slot - actual_adp (value_gap: positive = drafted early)
    system_value_slot       INTEGER,           -- system's recommended slot for this player
    tendency_label          VARCHAR NOT NULL,  -- human-readable warning string
    UNIQUE (league_id, tendency_type, COALESCE(position, ''), COALESCE(player_id, ''))
);
```

**Two tendency types:**

**Type 1: Positional run** — derived by comparing position draft frequency in league trade/draft history against the system's recommended positional ranking order.

```sql
-- Detect positional run tendencies
-- Compare avg pick slot where position was taken vs. system value slot
SELECT
    position,
    AVG(pick_slot) AS actual_avg_slot,
    AVG(system_value_slot) AS expected_avg_slot,
    AVG(system_value_slot) - AVG(pick_slot) AS slots_earlier,
    COUNT(*) AS sample_size
FROM historical_rookie_drafts hrd
JOIN rookie_board_cache rbc ON rbc.player_id = hrd.player_id
WHERE hrd.league_id = ?
  AND sample_size >= TENDENCY_MIN_SAMPLE_SIZE
GROUP BY position
HAVING ABS(slots_earlier) >= POSITIONAL_RUN_THRESHOLD
```

**Type 2: Value gap alert** — specific players who were consistently drafted significantly earlier than the system's recommended slot.

**Named constants in `rookie/constants.py`:**

```python
TENDENCY_MIN_SAMPLE_SIZE: int = 3      # minimum historical drafts to compute tendency
POSITIONAL_RUN_THRESHOLD: float = 1.2  # avg 1.2+ slots earlier = reportable positional tendency
VALUE_GAP_THRESHOLD: float = 2.0       # player taken 2+ slots earlier than system value
```

**Bootstrapping problem:** For leagues with no historical rookie draft data in the system (new leagues or leagues whose history was not ingested), the tendency table will be empty. The draft room handles this with the empty state: "No significant draft tendency patterns detected for this league yet." (specified in 07-UI-SPEC.md copywriting contract). The planner must ensure this empty state is handled as a first-class case, not a fallback.

---

## Database Schema — New Tables

### Table: `rookie_board_cache`

Stores computed board results per league per computation run. Allows the Phase 6 pick engine to read `class_strength_signal` without triggering a full board recompute on every pick valuation call.

```sql
CREATE TABLE IF NOT EXISTS rookie_board_cache (
    id                      INTEGER PRIMARY KEY,
    league_id               VARCHAR NOT NULL,
    computed_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    class_strength_signal   FLOAT NOT NULL DEFAULT 0.0,
    board_json              VARCHAR NOT NULL,  -- full serialized RookieBoardResult
    UNIQUE (league_id)  -- one cached board per league; upsert on recompute
);
```

### Table: `league_draft_tendencies`

Specified above. Alembic migration `008_rookie_board.py` creates both tables.

---

## API Endpoints

### `GET /rookie-board/{league_id}`

Returns the full board result pre-grouped by tier. Single batch response — no per-player calls.

**Response shape:**

```typescript
interface RookieBoardResponse {
  league_id: string
  league_format: string        // "PPR" | "Half PPR" | "Standard" | "Superflex"
  class_strength_signal: float // injected into Phase 6 pick engine
  tiers: RookieTier[]
  computed_at: string
}

interface RookieTier {
  tier_number: number          // 1-5
  label: string               // "Tier 1 — Elite" etc.
  players: RookiePlayer[]
}

interface RookiePlayer {
  player_id: string
  full_name: string
  position: string            // "WR" | "RB" | "QB" | "TE"
  archetype_label: string     // from ARCHETYPE_LABELS vocabulary
  risk_band: "Low" | "Moderate" | "High"
  composite_score: float
  tier_number: number
  available_probability_by_slot: Record<string, number>  // "1.01" -> 0.05, "1.06" -> 0.72, etc.
}
```

### `GET /draft-room/{league_id}/{pick_slot}`

Returns the three-question draft room answer. `pick_slot` is an integer (1 = 1.01, 6 = 1.06, etc.).

**Response shape:**

```typescript
interface DraftRoomResponse {
  league_id: string
  pick_slot: number
  trade_verdict: TradeVerdict
  best_in_abstract: RookiePlayer | null
  tendency_warnings: TendencyWarning[]
}

interface TradeVerdict {
  verdict: "trade" | "use"    // "trade" maps to "Trade it", "use" to "Use it"
  label: string               // "Trade it" | "Use it"
  reasoning: string           // one-line reasoning string from backend
}

interface TendencyWarning {
  warning_type: "positional_run" | "value_gap"
  title: string               // e.g. "WRs go early in this league"
  description: string         // e.g. "WRs taken 1.2 spots earlier on average vs. system value"
}
```

### `GET /picks/{league_id}` (Phase 6 — extended in Phase 7)

The existing endpoint is extended to populate `class_strength_signal` from `rookie_board_cache` instead of hardcoding `0.0`. No breaking change to the response shape.

---

## Draft Room Trade Verdict Logic

### Algorithm (CONFIDENCE: MEDIUM)

The trade verdict is a direct "Trade it" or "Use it" decision with a one-line reason. The inputs are:

1. Pick value from Phase 6 engine (already computed, stored in `pick_values` table)
2. Best available prospect value at this slot (from `rookie_board_cache`)
3. Class strength signal (from `rookie_board_cache`)

```python
# rookie/rookie_engine.py
def _compute_trade_verdict(
    self,
    league_id: str,
    pick_slot: int,
    board: RookieBoardResult,
) -> TradeVerdict:
    """
    "Trade it" wins when pick capital value > best available prospect value.
    "Use it" wins when a Tier 1 or strong Tier 2 player is available.
    Class strength modifies the threshold.
    """
    best_player = self._get_best_available_at_slot(board, pick_slot)

    if best_player is None:
        return TradeVerdict(
            verdict="trade",
            label="Trade it",
            reasoning="No significant prospects available at this slot — trade the pick",
        )

    # Pick value exceeds prospect value when:
    # - Pick slot is early (1.01-1.04) but no Tier 1 player is available
    # - Class strength is weak (negative signal)
    # - Pick has high demand in this league (from league_draft_tendencies)
    slot_has_tier1 = best_player.tier_number == 1
    slot_has_strong_tier2 = (
        best_player.tier_number == 2
        and best_player.composite_score >= STRONG_TIER2_THRESHOLD
    )
    class_is_weak = board.class_strength_signal < CLASS_WEAKNESS_THRESHOLD

    if slot_has_tier1 or slot_has_strong_tier2:
        return TradeVerdict(
            verdict="use",
            label="Use it",
            reasoning=self._use_reasoning(best_player, board.class_strength_signal),
        )

    if class_is_weak and pick_slot <= EARLY_PICK_VALUE_THRESHOLD:
        return TradeVerdict(
            verdict="trade",
            label="Trade it",
            reasoning="Class strength is weak this year — pick capital gains outweigh available prospects",
        )

    return TradeVerdict(
        verdict="trade",
        label="Trade it",
        reasoning=f"Your {self._format_slot(pick_slot)} carries more value than any available prospect here",
    )
```

**Named constants in `rookie/constants.py`:**

```python
STRONG_TIER2_THRESHOLD: float = 65.0   # composite score that qualifies as "strong Tier 2"
CLASS_WEAKNESS_THRESHOLD: float = -0.2  # class_strength_signal below this = weak class
EARLY_PICK_VALUE_THRESHOLD: int = 4     # pick slots 1-4 are "early" for trade verdict
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prospect data ingestion | Custom NFL draft API scraper | `players` table from Phase 1 + `player_stats_weekly` for college production | External scraping adds unreliable dependencies; Phase 1 already ingests player metadata |
| Class tier boundaries | Fixed thresholds (Tier 1 = top 5, etc.) | Gap-based dynamic tier assignment | Fixed thresholds produce wrong results in weak or strong class years; gap-based responds to actual score distribution |
| Draft tendency tracking | Manual CSV or hardcoded tendencies | `league_draft_tendencies` table computed from transaction history | Transaction history is already ingested (Phase 1 INGEST-05/06); building on that data is consistent with the tool's architecture |
| Available-at-slot simulation | Monte Carlo over remaining picks | Logistic heuristic on rank gap | Monte Carlo adds implementation complexity with marginal accuracy gain for this use case; community tools use rank-gap heuristics |
| Archetype label ML classification | Custom NLP or embedding model | Controlled vocabulary + rule-based assignment | Rules are transparent, auditable, and sufficient for Phase 7; Phase 8 backtested model can replace this |

---

## Common Pitfalls

### Pitfall 1: `traded_picks` vs. actual draft class rookies

The `traded_picks` table stores future picks (tradeable assets), not actual draft picks made in past rookie drafts. The rookie board needs actual rookie players in the current draft class, not the pick assets. These are different data entities.

**Resolution:** The rookie board uses the `players` table (where position is "WR"/"RB"/"QB"/"TE" and the player is a known NFL Draft prospect for the current year) combined with ADP data from `player_adp_baseline`. The `traded_picks` table is only used by the draft room to determine which pick slot the user holds.

### Pitfall 2: Empty draft class for leagues not yet in draft season

If the system has no current-year NFL Draft prospects in `player_adp_baseline` (because the ADP data is stale or the NFL Draft hasn't happened), `compute_board()` will return an empty board. The engine must return an empty result with a clear `board_status: "no_data"` flag rather than crashing. The frontend's empty state copy handles this: "No rookie class data loaded for this league yet."

### Pitfall 3: `class_strength_signal` injection timing

Phase 6 pick values are cached in `pick_values` table. If the rookie board is computed after the pick values were last cached, the `class_strength_signal` in `pick_values` will be stale (0.0 from Phase 6).

**Resolution:** When Phase 7 computes the rookie board, it must invalidate the `pick_values` cache by updating the `computed_at` field on `pick_values` rows to trigger recompute on next request. Alternatively, the pick value response can read `class_strength_signal` directly from `rookie_board_cache` at response time rather than from the cached `pick_values` row. The planner must decide which approach to use — the latter (live lookup at response time) is safer but slightly slower.

### Pitfall 4: league_draft_tendencies requires historical rookie drafts

Tendency analysis requires historical rookie draft data. Phase 1 ingestion covers trade history (`INGEST-05`) and transaction history (`INGEST-06`). Rookie draft results are a subset of transactions (`type='draft'`). The query must filter `transactions` for type 'draft' to extract historical pick order data.

If a league has not yet run any rookie drafts through this system (brand new league connection), the tendency table will be empty — this is correct behavior and must be handled as an expected case.

### Pitfall 5: Pick slot format mismatch

The draft room URL parameter is a raw integer (e.g. `6` for the 6th pick). The display format is `1.06`. The slot-to-display conversion must happen in a shared utility function, not duplicated across the backend response and frontend rendering. The backend should return `pick_slot_display: "1.06"` alongside `pick_slot: 6` in the response.

### Pitfall 6: Format badge derives from `leagues` table fields, not a hardcoded string

The format badge on the rookie board page displays the scoring format (e.g. "PPR", "Superflex"). This string must be derived from the `leagues` table columns (`ppr`, `superflex`, `tep`) — it cannot be a static string or a new `leagues.format_label` field. The `RookieEngine.compute_board()` must construct this badge label from existing column values.

**Derivation logic:**

```python
def _format_label(self, league_settings: dict) -> str:
    parts = []
    if league_settings.get("superflex"):
        parts.append("Superflex")
    if league_settings.get("tep"):
        parts.append("TEP")
    ppr = league_settings.get("ppr", 0.0)
    if ppr == 1.0:
        parts.append("PPR")
    elif ppr == 0.5:
        parts.append("Half PPR")
    else:
        parts.append("Standard")
    return " · ".join(parts)
```

### Pitfall 7: Navigation affordances break existing league drill-in tests

The league drill-in (`league.$leagueId.tsx`) is modified to add "Rookie Board" tab and "Enter Draft Room" button. Any existing tests that render `LeagueDetailPage` snapshot-style will fail because the rendered output changes. The plan must include a task to update tests after the navigation affordance changes.

---

## Code Examples

### Rookie Board DuckDB Query — Available Rookies

```sql
-- rookie_repo.py — get current draft class players
-- Reads from player_adp_baseline to identify current-year prospects
SELECT
    p.player_id,
    p.full_name,
    p.position,
    p.age,
    p.team,
    adp.adp,
    adp.adp_source
FROM players p
JOIN player_adp_baseline adp ON adp.player_id = p.player_id
WHERE p.position IN ('WR', 'RB', 'QB', 'TE')
  AND adp.adp IS NOT NULL
ORDER BY adp.adp ASC
```

### Rookie Board DuckDB Query — Historical Rookie Draft Tendencies

```sql
-- rookie_repo.py — compute positional tendency from past rookie drafts
-- Transactions of type 'draft' contain the pick history
SELECT
    p.position,
    AVG(CAST(REPLACE(json_extract(t.draft_picks, '$[*].round'), '"', '') AS INTEGER)) AS avg_actual_round,
    COUNT(*) AS pick_count
FROM transactions t
JOIN players p ON json_extract(t.adds, '$.*') LIKE '%' || p.player_id || '%'
WHERE t.league_id = ?
  AND t.type = 'draft'
  AND t.status = 'complete'
GROUP BY p.position
HAVING pick_count >= ?
```

### TanStack Router — Draft Room with Query Param Pre-population

```typescript
// frontend/src/routes/draft-room.tsx
export const Route = createFileRoute("/draft-room")({
  validateSearch: (search: Record<string, unknown>) => ({
    leagueId: typeof search.leagueId === "string" ? search.leagueId : undefined,
  }),
  component: DraftRoomPage,
})

function DraftRoomPage() {
  const { leagueId: initialLeagueId } = Route.useSearch()
  const [selectedLeagueId, setSelectedLeagueId] = useState(initialLeagueId ?? "")
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null)
  // ...
}
```

### Frontend — Slot Availability Highlight (Client-Side)

```typescript
// AVAILABILITY_THRESHOLD is a named constant
const AVAILABILITY_THRESHOLD = 0.5

function isAvailableAtSlot(player: RookiePlayer, slot: string): boolean {
  return (player.available_probability_by_slot[slot] ?? 0) >= AVAILABILITY_THRESHOLD
}
```

### VerdictBanner — Reuses StrategicDistinctionBanner Visual Pattern

Per 07-UI-SPEC.md and the existing `StrategicDistinctionBanner` component in `frontend/src/components/trade/StrategicDistinctionBanner.tsx`, the VerdictBanner follows the same visual layout (colored background, verdict label, reasoning string) with different color tokens and Display-sized text. Read the existing component before implementing VerdictBanner.

---

## Navigation Affordances — Exact Changes Required

### `league.$leagueId.tsx` changes (two additions)

1. Add "Rookie Board" navigation — a tab or link navigating to `/league/$leagueId/rookie-board`
2. Add "Enter Draft Room" button — `Button variant="ghost" size="sm"` with Lucide `Clipboard` icon navigating to `/draft-room?leagueId={leagueId}`

The current `league.$leagueId.tsx` has two buttons in `CardHeader` action area: "View Managers" and "Evaluate Trade". Phase 7 adds two more affordances in the same area. Per 07-UI-SPEC.md, the Draft Room button is NOT a tab — it is a standalone `Button` that communicates the draft room is a separate decision tool, not a league view.

### `__root.tsx` — no change required

The root nav currently has "Dashboard" and "Evaluate Trade". Phase 7 does not add "Draft Room" to global nav (per D-08 — accessed from league drill-in, not top-level nav).

---

## Integration Points Summary

| Integration | From | To | What Changes |
|-------------|------|----|-------------|
| Class strength injection | `RookieEngine.compute_board()` | `PickValuationContext.class_strength_signal` | Phase 7 writes real float to `rookie_board_cache`; Phase 6 `PickRepo` reads it |
| Pick values recompute trigger | `POST /rookie-board/{league_id}/compute` | `pick_values` table | Board recompute should invalidate pick_values cache for the league |
| League drill-in navigation | `league.$leagueId.tsx` | `/league/$leagueId/rookie-board` and `/draft-room` | Two new navigation affordances added to existing card header |
| Draft room pick slots | `GET /picks/{league_id}` | Draft room `Select` options | Pick slot list comes from existing picks endpoint — no new data fetch |
| Draft room league selector | Existing dashboard league list | Draft room `Select` options | Reuses already-fetched league data — no new endpoint needed |

---

## Plan Wave Structure (Recommended)

Based on the dependency graph and the established Phase 6 pattern of 4 plans across 4 waves:

| Wave | Plans | What | Autonomous |
|------|-------|------|------------|
| 1 | Plan 01 | Backend foundation: `rookie/` package constants, models, `RookieRepo`, Alembic migration 008 (two new tables) | Yes |
| 2 | Plan 02 | Backend engine: `RookieEngine.compute_board()`, `compute_class_strength()`, tier assignment, archetype/risk assignment | Yes |
| 3 | Plan 03 | Backend draft room: `compute_draft_room()`, trade verdict logic, tendency analysis; `/rookie-board` and `/draft-room` routers; inject class_strength into Phase 6 pick engine | Yes |
| 4 | Plan 04 | Frontend: two new routes, RookiePlayerCard, TierDivider, TierGroup, VerdictBanner, TendencyWarningList, TanStack Query hooks, league drill-in navigation affordances | No (human verify) |

This mirrors the Phase 6 wave structure exactly (foundation → engine → router → frontend).

---

## Sources Consulted

- 07-CONTEXT.md — locked decisions, descoped items, code context, integration points (HIGH)
- 07-UI-SPEC.md — component inventory, routing structure, copywriting contract, interaction states (HIGH)
- 06-CONTEXT.md — class_strength hook interface spec, D-01/D-02, Phase 7 integration notes (HIGH)
- 06-RESEARCH.md — PickValuationContext model, class_strength_signal field spec, established formula patterns (HIGH)
- 06-01-PLAN.md through 06-04-PLAN.md — wave structure pattern, plan format, established artifact conventions (HIGH)
- `backend/src/fantasy/main.py` — router registration pattern (HIGH)
- `backend/src/fantasy/routers/deps.py` — DuckDB dependency injection pattern (HIGH)
- `backend/src/fantasy/intelligence/models.py` — Pydantic model conventions (HIGH)
- `backend/src/fantasy/db/models.py` — existing table schemas including `traded_picks`, `standings`, `transactions` (HIGH)
- `frontend/src/routes/league.$leagueId.tsx` — existing league drill-in structure to be extended (HIGH)
- `frontend/src/routes/trades.tsx` — standalone route pattern for draft room (HIGH)
- `frontend/src/routes/league.$leagueId.managers.tsx` — nested route pattern for rookie board (HIGH)
- `frontend/src/api/queries.ts` — TanStack Query hook conventions and staleTime patterns (HIGH)
- `frontend/src/api/types.ts` — TypeScript interface conventions (HIGH)
- DynastyProcess.com tier assignment methodology (gap-based tier breakpoints) — MEDIUM
- Fantasy Footballers "How to Value the Rookie Draft Class" (class strength assessment, archetype patterns) — MEDIUM
- The Undroppables "Art of Dynasty Chapter 4" (tiered board structure, archetype labels, risk bands) — MEDIUM

---

*Phase: 07-rookie-board-draft-room*
*Researched: 2026-03-22*
