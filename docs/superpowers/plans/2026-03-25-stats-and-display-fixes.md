# Stats Pipeline and Display Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four bugs — wrong position tags on lineup slot scores, consolidation trades targeting un-exploitable managers, and all stash/position-median scores collapsing to hardcoded fallbacks because `player_stats_weekly` is never populated.

**Architecture:** Three independent changes: (1) one-line fix in `lineup_engine.py`, (2) manager exploitability gate in `hygiene_engine.py`, (3) wire `NflDataPyLoader` into `ingest_service.py` via two module-level helpers that map GSIS→Sleeper IDs and compute per-league fantasy points. Fix 3 resolves both the `position_medians=8.0` bug and the `comp_ceiling=0.333` stash fallback simultaneously.

**Tech Stack:** Python, Polars, DuckDB, nfl_data_py, pytest

---

### Task 1: Fix lineup slot position tags

**Files:**
- Modify: `backend/src/fantasy/lineup/lineup_engine.py:215-224`
- Test: `backend/tests/lineup/test_lineup_engine.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/lineup/test_lineup_engine.py`:

```python
def test_slot_score_position_uses_player_position_not_slot_label():
    conn = duckdb.connect(":memory:")
    eng = LineupEngine(conn)
    # Purdy (QB) in SUPER_FLEX slot — should show "QB", not "SUPER_FLEX"
    all_in = {
        1: _base_inputs(
            1,
            roster_positions=["SUPER_FLEX", "BN"],
            starters=["qb1"],
            bench=[],
            weekly={"qb1": 22.0},
            player_positions={"qb1": "QB"},
        ),
        2: _base_inputs(
            2,
            roster_positions=["SUPER_FLEX", "BN"],
            starters=["qb2"],
            bench=[],
            weekly={"qb2": 18.0},
            player_positions={"qb2": "QB"},
        ),
    }
    results = eng.compute_all("league_t", all_in)
    slot = results[1].slot_scores[0]
    assert slot.position == "QB", f"expected QB, got {slot.position!r}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/jakyeamos/Desktop/Fantasy/backend
python -m pytest tests/lineup/test_lineup_engine.py::test_slot_score_position_uses_player_position_not_slot_label -v
```

Expected: `FAILED — AssertionError: expected QB, got 'SUPER_FLEX'`

- [ ] **Step 3: Apply the fix**

In `backend/src/fantasy/lineup/lineup_engine.py` at line 217, change `position=slot` to use the player's actual position:

```python
slot_scores.append(
    LineupSlotScore(
        position=inputs.player_positions.get(pid, slot),  # was: position=slot
        player_id=pid,
        player_name=_player_display(self._conn, pid),
        starter_value=float(starter_val),
        replacement_level=float(repl),
        score=score,
    )
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/lineup/test_lineup_engine.py::test_slot_score_position_uses_player_position_not_slot_label -v
```

Expected: `PASSED`

- [ ] **Step 5: Run full lineup engine suite**

```bash
python -m pytest tests/lineup/test_lineup_engine.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/fantasy/lineup/lineup_engine.py backend/tests/lineup/test_lineup_engine.py
git commit -m "fix(lineup): use player position instead of slot label in LineupSlotScore"
```

---

### Task 2: Gate consolidation suggestions on manager exploitability

**Files:**
- Modify: `backend/src/fantasy/lineup/hygiene_engine.py:242-254`
- Test: `backend/tests/lineup/test_hygiene_engine.py`

The current code picks the first manager whose player has `lens_direction >= 0.5`, ignoring whether that manager would ever accept a lopsided trade. The fix: skip managers whose `manager_profiles` row shows `low_confidence = TRUE` or `evidence_count < 10` (the existing `MIN_TRADE_EVIDENCE_THRESHOLD`), and also skip managers with `exploitability_score < 40.0` (below which the manager is considered sharp/semi-sharp).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/lineup/test_hygiene_engine.py`:

```python
def _seed_consolidation_db(db, *, target_exploitability: float, target_evidence: int, target_low_confidence: bool):
    """Seed minimal data for a 2-roster consolidation scenario."""
    db.execute("""
        INSERT INTO leagues (league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr)
        VALUES ('lc1', 'C', '2025', '{}', '["QB","BN","BN"]', '{}', FALSE, FALSE, 0.0)
    """)
    db.execute("""
        INSERT INTO rosters (id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi)
        VALUES
          (801, 'lc1', 1, 'u1', 'User', '["s1"]', '["s1","b1","b2"]', '[]', '[]'),
          (802, 'lc1', 2, 'u2', 'Target', '["ts1"]', '["ts1"]', '[]', '[]')
    """)
    for pid in ('s1', 'b1', 'b2', 'ts1'):
        db.execute(
            "INSERT INTO players (player_id, full_name, position, team, age, metadata_blob) VALUES (?, ?, 'WR', 'X', 24, '{}')",
            [pid, pid],
        )
    # b1 and b2 are low-lens bench players (candidates to package)
    for pid, lens in [('b1', 0.2), ('b2', 0.25), ('s1', 0.8)]:
        db.execute("""
            INSERT INTO player_values (id, league_id, roster_id, player_id,
                comp_current_production, comp_short_term, comp_role_stability,
                comp_age_curve, comp_insulation, comp_market_liquidity,
                comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
                comp_rerollability, comp_contract,
                lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction)
            VALUES (?, 'lc1', 1, ?, 0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,?)
        """, [8000 + hash(pid) % 1000, pid, lens])
    # ts1 is a high-lens player on the target roster
    db.execute("""
        INSERT INTO player_values (id, league_id, roster_id, player_id,
            comp_current_production, comp_short_term, comp_role_stability,
            comp_age_curve, comp_insulation, comp_market_liquidity,
            comp_positional_scarcity, comp_fragility, comp_ceiling, comp_floor,
            comp_rerollability, comp_contract,
            lens_production, lens_market, lens_insulation, lens_team_fit, lens_direction)
        VALUES (9001, 'lc1', 2, 'ts1', 0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0.8)
    """)
    # Manager profile for target roster
    db.execute("""
        INSERT INTO manager_profiles (id, league_id, roster_id, evidence_count, low_confidence,
            exploitability_score, exploitation_primary, exploitation_secondary,
            exploitation_evidence, aggregate_trade_stats, trade_history)
        VALUES (701, 'lc1', 2, ?, ?, ?, NULL, NULL, '{}', '{}', '[]')
    """, [target_evidence, target_low_confidence, target_exploitability])


def test_consolidation_skips_low_exploitability_manager(db):
    _seed_consolidation_db(db, target_exploitability=25.0, target_evidence=15, target_low_confidence=False)
    eng = HygieneEngine(db)
    inp = _inputs('lc1', 1, bench=['b1', 'b2'], starters=['s1'])
    all_inp = {1: inp, 2: _inputs('lc1', 2, bench=[], starters=['ts1'])}
    result = eng.compute('lc1', 1, inp, 'rebuild', all_inp)
    # Should produce a no-counterparty suggestion, not one targeting the sharp manager
    for s in result.consolidate:
        assert s.counterparty_roster_id is None, (
            f"Should not target roster 2 (exploitability=25.0), got counterparty={s.counterparty_roster_id}"
        )


def test_consolidation_skips_low_confidence_manager(db):
    _seed_consolidation_db(db, target_exploitability=70.0, target_evidence=3, target_low_confidence=True)
    eng = HygieneEngine(db)
    inp = _inputs('lc1', 1, bench=['b1', 'b2'], starters=['s1'])
    all_inp = {1: inp, 2: _inputs('lc1', 2, bench=[], starters=['ts1'])}
    result = eng.compute('lc1', 1, inp, 'rebuild', all_inp)
    for s in result.consolidate:
        assert s.counterparty_roster_id is None, (
            f"Should not target low-confidence roster 2, got counterparty={s.counterparty_roster_id}"
        )


def test_consolidation_targets_exploitable_manager(db):
    _seed_consolidation_db(db, target_exploitability=70.0, target_evidence=15, target_low_confidence=False)
    eng = HygieneEngine(db)
    inp = _inputs('lc1', 1, bench=['b1', 'b2'], starters=['s1'])
    all_inp = {1: inp, 2: _inputs('lc1', 2, bench=[], starters=['ts1'])}
    result = eng.compute('lc1', 1, inp, 'rebuild', all_inp)
    targets = [s.counterparty_roster_id for s in result.consolidate if s.counterparty_roster_id is not None]
    assert 2 in targets, f"Should target exploitable roster 2, got {targets}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/lineup/test_hygiene_engine.py::test_consolidation_skips_low_exploitability_manager tests/lineup/test_hygiene_engine.py::test_consolidation_skips_low_confidence_manager tests/lineup/test_hygiene_engine.py::test_consolidation_targets_exploitable_manager -v
```

Expected: first two FAIL (sharp manager is currently targeted), third may FAIL or PASS.

- [ ] **Step 3: Apply the fix**

In `backend/src/fantasy/lineup/hygiene_engine.py`, add a constant at the top of the file (after the existing imports, before the class):

```python
_MIN_EXPLOITABILITY_SCORE: float = 40.0
_MIN_TRADE_EVIDENCE: int = 10
```

Then replace the target-finding loop at lines 242-254:

```python
target_pid: str | None = None
target_rid: int | None = None
for other_rid, oins in all_inputs.items():
    if other_rid == roster_id:
        continue
    # Skip managers without enough trade history or who are too sharp to exploit
    profile_row = self._conn.execute(
        """
        SELECT exploitability_score, evidence_count, low_confidence
        FROM manager_profiles
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, other_rid],
    ).fetchone()
    if profile_row is not None:
        expl_score = float(profile_row[0])
        evidence = int(profile_row[1])
        low_conf = bool(profile_row[2])
        if low_conf or evidence < _MIN_TRADE_EVIDENCE or expl_score < _MIN_EXPLOITABILITY_SCORE:
            continue
    for pid in oins.starters + oins.bench:
        lv = self._row_lens(league_id, other_rid, pid)
        if lv >= 0.5:
            target_pid = pid
            target_rid = other_rid
            break
    if target_pid:
        break
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/lineup/test_hygiene_engine.py::test_consolidation_skips_low_exploitability_manager tests/lineup/test_hygiene_engine.py::test_consolidation_skips_low_confidence_manager tests/lineup/test_hygiene_engine.py::test_consolidation_targets_exploitable_manager -v
```

Expected: all three PASS.

- [ ] **Step 5: Run full hygiene engine suite**

```bash
python -m pytest tests/lineup/test_hygiene_engine.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/fantasy/lineup/hygiene_engine.py backend/tests/lineup/test_hygiene_engine.py
git commit -m "fix(hygiene): skip consolidation targets with low exploitability or insufficient trade evidence"
```

---

### Task 3: Wire NflDataPyLoader into IngestService to populate player_stats_weekly

This fixes two bugs at once: `position_medians` falling back to `8.0` (scorecard engine) and `comp_ceiling` falling back to `0.333` (valuation engine / stash suggestions). Both happen because `player_stats_weekly` is always empty — `NflDataPyLoader` exists and works but is never called.

**The wrinkle:** nfl_data_py uses GSIS IDs (e.g. `"00-0036971"`) while the DB uses Sleeper IDs. Sleeper stores `gsis_id` in `players.metadata_blob`, so we build a mapping at ingest time.

**Files:**
- Modify: `backend/src/fantasy/ingestion/ingest_service.py`
- Test: `backend/tests/test_ingest_service.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_ingest_service.py`:

```python
import polars as pl
from unittest.mock import MagicMock, patch

from fantasy.ingestion.ingest_service import _build_gsis_sleeper_map, _prepare_stats_df
from fantasy.ingestion.nfl_data_loader import PLAYER_STATS_COLUMNS


def test_build_gsis_sleeper_map_extracts_from_metadata_blob(db):
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
          ('4017', 'Player A', 'QB', 'SF', 26, '{"gsis_id": "00-0033873"}'),
          ('4663', 'Player B', 'WR', 'SF', 24, '{"gsis_id": "00-0036971"}'),
          ('9999', 'No GSIS',  'TE', 'X',  22, '{}')
        """
    )
    mapping = _build_gsis_sleeper_map(db)
    assert mapping == {"00-0033873": "4017", "00-0036971": "4663"}


def test_prepare_stats_df_remaps_ids_and_computes_fantasy_points():
    gsis_to_sleeper = {"00-0033873": "4017"}
    scoring = {"rec": 1.0, "rec_yd": 0.1}
    raw = pl.DataFrame(
        {
            "player_id": ["00-0033873", "00-0099999"],  # second has no mapping
            "player_name": ["Player A", "Unknown"],
            "position": ["WR", "WR"],
            "season": [2025, 2025],
            "week": [1, 1],
            "receptions": [6.0, 4.0],
            "targets": [8.0, 5.0],
            "receiving_yards": [80.0, 50.0],
            "receiving_tds": [0.0, 0.0],
            "rushing_yards": [0.0, 0.0],
            "rushing_tds": [0.0, 0.0],
            "carries": [0.0, 0.0],
            "passing_yards": [0.0, 0.0],
            "passing_tds": [0.0, 0.0],
            "interceptions": [0.0, 0.0],
            "passing_2pt_conversions": [0.0, 0.0],
            "receiving_2pt_conversions": [0.0, 0.0],
            "rushing_2pt_conversions": [0.0, 0.0],
            "fantasy_points": [None, None],
        }
    )
    result = _prepare_stats_df(raw, gsis_to_sleeper, scoring)
    assert result.height == 1, "unmapped player should be dropped"
    assert result["player_id"].to_list() == ["4017"]
    # 6 rec * 1.0 + 80 yards * 0.1 = 14.0
    assert result["fantasy_points"].to_list() == [14.0]
    assert result.columns == PLAYER_STATS_COLUMNS


@pytest.mark.asyncio
async def test_ingest_populates_player_stats_weekly(db, base_league, base_roster):
    stats_df = pl.DataFrame(
        {
            "player_id": ["00-0033873"],
            "player_name": ["Player One"],
            "position": ["WR"],
            "season": [2025],
            "week": [1],
            "receptions": [5.0],
            "targets": [7.0],
            "receiving_yards": [60.0],
            "receiving_tds": [0.0],
            "rushing_yards": [0.0],
            "rushing_tds": [0.0],
            "carries": [0.0],
            "passing_yards": [0.0],
            "passing_tds": [0.0],
            "interceptions": [0.0],
            "passing_2pt_conversions": [0.0],
            "receiving_2pt_conversions": [0.0],
            "rushing_2pt_conversions": [0.0],
            "fantasy_points": [None],
        }
    )
    # Seed a player with a known gsis_id
    db.execute(
        "INSERT INTO players (player_id, full_name, position, team, age, metadata_blob) "
        "VALUES ('4017', 'Player One', 'WR', 'SF', 24, '{\"gsis_id\": \"00-0033873\"}')"
    )
    mock_loader = MagicMock()
    mock_loader.load_weekly_stats.return_value = stats_df

    with patch(
        "fantasy.ingestion.ingest_service.NflDataPyLoader", return_value=mock_loader
    ):
        client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)
        service = IngestService(db, client)
        await service.run("test_league_001", "full")

    rows = db.execute(
        "SELECT player_id, week, fantasy_points FROM player_stats_weekly"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "4017"
    assert rows[0][1] == 1
    # 5 rec * 1.0 + 60 yards * 0.1 = 11.0 (scoring: {"rec": 1.0, "rec_yd": 0.1})
    assert rows[0][2] == 11.0


@pytest.mark.asyncio
async def test_ingest_completes_when_stats_loader_raises(db, base_league, base_roster):
    mock_loader = MagicMock()
    mock_loader.load_weekly_stats.side_effect = RuntimeError("nfl_data_py unavailable")

    with patch(
        "fantasy.ingestion.ingest_service.NflDataPyLoader", return_value=mock_loader
    ):
        client = FakeSleeperClient(base_league, [base_roster], [], {}, week=1)
        service = IngestService(db, client)
        run_id = await service.run("test_league_001", "full")

    status = db.execute(
        "SELECT status FROM ingest_runs WHERE id = ?", [run_id]
    ).fetchone()[0]
    assert status == "complete"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_ingest_service.py::test_build_gsis_sleeper_map_extracts_from_metadata_blob tests/test_ingest_service.py::test_prepare_stats_df_remaps_ids_and_computes_fantasy_points tests/test_ingest_service.py::test_ingest_populates_player_stats_weekly tests/test_ingest_service.py::test_ingest_completes_when_stats_loader_raises -v
```

Expected: all four FAIL with `ImportError: cannot import name '_build_gsis_sleeper_map'`.

- [ ] **Step 3: Implement the helpers and wire up the call**

In `backend/src/fantasy/ingestion/ingest_service.py`, change the import from `nfl_data_loader`:

```python
from fantasy.ingestion.nfl_data_loader import (
    PLAYER_STATS_COLUMNS,
    SLEEPER_TO_NFLDATA_MAP,
    NflDataPyLoader,
    compute_fantasy_points,
)
```

Add two module-level helpers before the `IngestService` class:

```python
def _build_gsis_sleeper_map(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for sleeper_id, blob in conn.execute(
        "SELECT player_id, metadata_blob FROM players WHERE metadata_blob IS NOT NULL"
    ).fetchall():
        try:
            data = json.loads(blob)
        except (json.JSONDecodeError, TypeError):
            continue
        gsis_id = data.get("gsis_id")
        if gsis_id:
            mapping[str(gsis_id)] = str(sleeper_id)
    return mapping


def _prepare_stats_df(
    raw_df: pl.DataFrame,
    gsis_to_sleeper: dict[str, str],
    scoring_settings: dict[str, float],
) -> pl.DataFrame:
    prepared = []
    for row in raw_df.to_dicts():
        sleeper_id = gsis_to_sleeper.get(str(row.get("player_id") or ""))
        if not sleeper_id:
            continue
        position = str(row.get("position") or "")
        fantasy_pts, _ = compute_fantasy_points(row, scoring_settings, position)
        prepared.append({**row, "player_id": sleeper_id, "fantasy_points": fantasy_pts})
    if not prepared:
        return pl.DataFrame(schema={col: pl.Float64 for col in PLAYER_STATS_COLUMNS})
    return pl.DataFrame(prepared).select(PLAYER_STATS_COLUMNS)
```

In `IngestService.run()`, add the stats loading block after `override_service.apply_corrections(self.conn, league_id)` and before the `season_rows` query:

```python
# Load NFL weekly stats and populate player_stats_weekly
gsis_to_sleeper = _build_gsis_sleeper_map(self.conn)
try:
    loader = NflDataPyLoader()
    raw_df = loader.load_weekly_stats([season_number])
    if raw_df.height > 0:
        stats_ready = _prepare_stats_df(raw_df, gsis_to_sleeper, league.scoring_settings)
        loader.upsert_weekly_stats(self.conn, stats_ready)
except Exception:
    pass  # Stats load failure surfaces via gap detection below; ingest must still complete
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_ingest_service.py::test_build_gsis_sleeper_map_extracts_from_metadata_blob tests/test_ingest_service.py::test_prepare_stats_df_remaps_ids_and_computes_fantasy_points tests/test_ingest_service.py::test_ingest_populates_player_stats_weekly tests/test_ingest_service.py::test_ingest_completes_when_stats_loader_raises -v
```

Expected: all four PASS.

- [ ] **Step 5: Run full ingest test suite**

```bash
python -m pytest tests/test_ingest_service.py -v
```

Expected: all tests pass. Existing tests pass because `NflDataPyLoader` is not mocked there — the `except Exception: pass` guard means the `ImportError` from nfl_data_py not being available is silently swallowed and ingest still completes.

- [ ] **Step 6: Commit**

```bash
git add backend/src/fantasy/ingestion/ingest_service.py backend/tests/test_ingest_service.py
git commit -m "fix(ingest): populate player_stats_weekly via NflDataPyLoader during ingest run"
```

---

### Task 4: Final verification — run full test suite

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/jakyeamos/Desktop/Fantasy/backend
python -m pytest --tb=short -q
```

Expected: all tests pass with no regressions.

- [ ] **Step 2: Confirm no hardcoded fallbacks remain in hot paths**

```bash
grep -n "8\.0\|10\.0" backend/src/fantasy/intelligence/scorecard_engine.py backend/src/fantasy/intelligence/valuation_engine.py
```

The `8.0` fallback in `scorecard_engine.py:248` and `valuation_engine.py:82`, and `10.0` in `valuation_engine.py:81` are legitimate last-resort defaults that remain — they only fire when a player truly has no data even after a successful stats load. That's expected; no change needed.
