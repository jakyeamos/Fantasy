# Project Research Summary

**Project:** Dynasty Fantasy Football Front Office OS
**Domain:** Personal sports analytics — local web app (Python backend + React dashboard)
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

This is a personal intelligence tool for dynasty fantasy football managers, built as a local Python + React web application against the Sleeper public API. Research shows that no existing tool in the market (KeepTradeCut, FantasyCalc, DynastyNerds, Dynasty Daddy) integrates team direction detection, manager behavior profiling, league-specific value adjustment, dynamic pick valuation, and prospect research into a single opinionated recommendation layer. Every competitor stops at data display. The differentiated value proposition here is telling the user *what to do next*, given their specific roster, league, and counterparties — a gap confirmed by direct analysis of competitor feature sets. The recommended architecture is a six-engine analytics platform behind a FastAPI HTTP layer, backed by DuckDB for analytical storage, with a clean platform adapter pattern that keeps Sleeper-specific code isolated and future platform additions mechanical.

The recommended stack is Python 3.12 / FastAPI / DuckDB / Polars on the backend and React 19 / Vite / TanStack Query / shadcn+ui on the frontend. DuckDB is the decisive database choice over SQLite — this system's query patterns are almost entirely analytical (aggregations, time series, cross-league joins), and DuckDB is 10–17x faster for these workloads with no infrastructure overhead. The adapter-first architecture is equally decisive: all Sleeper-specific JSON parsing lives in one mapper module, and all six analysis engines consume only internal Pydantic domain models. This means platform changes require zero engine modifications.

The dominant risk is building too many engines before validating the core direction detection model on real league data. If the team direction labels don't match a manager's own read of their situation, every downstream recommendation is wrong — and that miscalibration won't be discovered until Phase 2 is already built on top of it. The second critical risk is false precision: dynasty valuation is probabilistic, and producing clean single-number outputs instead of confidence bands and sub-score breakdowns destroys trust at the moment the model makes a wrong call. Both risks must be addressed in Phase 1 — by enforcing a validation gate before Phase 2 begins and by designing confidence-first output schemas from the first endpoint.

---

## Key Findings

### Recommended Stack

The backend runs Python 3.12 + FastAPI (async-native, Pydantic-integrated) + DuckDB (OLAP, single-file, no daemon) + Polars (Rust-based DataFrame engine for all analytics computation). httpx replaces `requests` in all async FastAPI contexts — using `requests` inside an ASGI server blocks the event loop. APScheduler runs scheduled Sleeper ingestion inside the FastAPI process without requiring Celery or Redis. SQLModel unifies Pydantic validation models and database schema definitions in a single class definition.

The frontend runs React 19 + Vite 6 + TypeScript + TanStack Query (server state) + Zustand (UI state) + shadcn/ui + Recharts. The TanStack Query / Zustand split is deliberate and important: TanStack Query owns everything fetched from the FastAPI backend; Zustand owns only pure UI state (selected league, open panels). Mixing these causes cache invalidation problems. CRA is abandoned — Vite only.

**Core technologies:**
- Python 3.12 + FastAPI 0.135: async HTTP API, Pydantic-native validation, auto OpenAPI docs
- DuckDB 1.5.0: in-process OLAP database — the correct choice over SQLite for analytical query patterns
- Polars 1.38.1: primary analytics DataFrame engine — 5–10x faster than pandas, multi-threaded, Arrow-backed
- SQLModel 0.0.22+: unified Pydantic + SQLAlchemy ORM layer; single class = validation model + DB schema
- httpx 0.28+: async Sleeper API client — required; `requests` blocks the event loop
- APScheduler 3.10+: in-process scheduled sync — no Celery/Redis needed for single-user local app
- React 19.2 + Vite 6 + TypeScript 5: modern React stack; CRA is deprecated and must not be used
- TanStack Query v5: server-state management for all FastAPI data; handles caching, refetch, stale state
- Zustand v5: UI-only state; never put server data here
- shadcn/ui + Tailwind 4 + Recharts 3: component primitives, styling, charting — zero runtime overhead
- uv + Ruff: modern Python toolchain (Rust-based); replaces pip+virtualenv and flake8+black

### Expected Features

**Must have (table stakes — Phases 1–2):**
- Sleeper league ingestion (rosters, picks, standings, format settings) — root dependency for everything
- Format flags as first-class inputs (superflex, TEP, premium scoring) — affects all downstream valuation
- Team scorecard with decomposed sub-scores (win-now, future value, depth, pick capital, flexibility, fragility, age risk)
- Team direction detection with confidence score, reasoning, and alternate paths — the primary thesis differentiator
- Trade evaluator with direction fit and roster fit (not just raw value comparison)
- Manager dossier per leaguemate (trade tendencies, overpay patterns, pitch angles)
- Dashboard: direction labels, top 3 action items per team, value risers/fallers
- Basic pick valuations (early/mid/late tier by year)
- Manual correction support everywhere — required before any analysis is trusted

**Should have (competitive differentiators — Phase 3):**
- Dynamic pick engine: class strength, rebuilder count, standings-based valuation
- Rookie board with format-aware tiers and roster-fit overlays
- Package builder with manager-specific opening offers
- Pick timing recommendations (sell/hold/use)
- Portfolio exposure dashboard with correlated risk flags

**Defer (v2+ — Phases 4–5):**
- Historical prospect database (10+ years, backtested position models)
- Hit-rate models with archetype clustering and comps
- Recommendation retrospectives (requires Phase 1–3 to have produced outcomes worth grading)
- Manager behavior trend persistence across seasons

**Anti-features (explicitly not building):**
- Automated trade offer sending (Sleeper API is read-only for trade submission)
- Public rankings aggregator (turns personal intelligence tool into content site)
- Multi-platform ingestion in v1 (Sleeper first; adapter pattern enables ESPN/Yahoo later with zero engine changes)
- Weekly start/sit optimizer (dynasty-focused product; redraft optimization is commoditized elsewhere)

### Architecture Approach

The architecture separates concerns into four independent layers: a Platform Adapter Layer (SleeperMapper translates raw Sleeper JSON to internal domain models — the only code that knows Sleeper's JSON shape), a Domain Model Layer (Pydantic structs that are the contract for everything downstream), an Engine Layer (six isolated engines that accept domain models and return typed outputs with confidence scores), and an Engine Orchestrator (resolves dependency order, threads engine outputs into later engines, composes final recommendations). The React frontend never touches the DB — all data flows through the FastAPI HTTP layer, cached by TanStack Query. Analysis is on-demand; data sync is scheduled separately. Snapshots are append-only (never UPDATE team_snapshots), enabling retrospectives without audit infrastructure.

**Major components:**
1. SleeperAdapter (client + mapper) — translates Sleeper API responses to domain models; isolated so platform changes require zero engine updates
2. Engine Orchestrator — runs E2 (League Context) and E1 (Global Baseline) first; threads into E3 (Team Direction), then E4 (Manager Behavior) and E5 (Trade Pathing); E6 (Prospect Research) is independent
3. DuckDB + Repository Layer — analytical storage; engines call repositories, never write SQL directly; Alembic manages schema evolution
4. APScheduler (Sync Scheduler) — in-process scheduled Sleeper ingest; separate from analysis pipeline; sets data freshness flags
5. FastAPI Router Layer — thin HTTP boundary; validates input, calls orchestrator, serializes Pydantic models to JSON
6. React Frontend (TanStack Query + Zustand) — renders recommendations; TanStack Query caches all server state; Zustand holds only UI state

### Critical Pitfalls

1. **False precision in dynasty valuation** — Design confidence-first output schemas in Phase 1 before any engine is built. Every output must carry a confidence band, sub-score breakdown, and "what breaks this thesis" note. Never show a single integer as a player value. Recovery cost is HIGH if deferred — all downstream engines inherit the problem.

2. **Building engines before validating the core direction model** — Enforce a hard phase gate: direction labels must be manually reviewed against all active leagues before Phase 2 scope opens. If the direction engine labels a clear rebuild as a contender, every trade recommendation built on top of it is wrong. Recovery cost is HIGH — Phase 2 must be rebuilt.

3. **Sleeper API data gaps treated as complete data** — The player stats endpoint is deprecated from Sleeper's open API. The trade history pick objects have inconsistent `previous_owner_id` fields. Build an explicit data completeness layer in the ingest pipeline (Phase 1). Every data domain must have a health check that surfaces gaps. Null handling must be tested with incomplete response fixtures before any engine consumes the data.

4. **Manager dossier inference from insufficient transaction history** — A manager with 3–5 trades does not have an established behavioral profile. All dossiers must display their evidence count prominently. Recommendations must be suppressed or labeled LOW confidence below the 10-trade threshold. Profile confidence must decay with sample size, not remain flat.

5. **UI complexity creep burying recommendations** — Design the dashboard from the recommendation down, not from the data up. The first visible screen of any league card must show direction label + top 3 action items. Sub-scores must be collapsible. Every added data panel must justify whether it changes the decision the user makes — if not, it belongs in a drill-down.

---

## Implications for Roadmap

Based on research, the dependency graph from FEATURES.md and the build order from ARCHITECTURE.md converge on a five-phase structure. The order is driven by hard dependencies: the adapter and ingestion layer must exist before any engine can run; E2 (League Context) and E1 (Global Baseline) must exist before E3 (Team Direction); E3 must be validated before E4 and E5 are built; E6 (Prospect Research) is partially independent but its dynamic pick engine requires standing data from the core pipeline.

### Phase 1: Foundation — Data Ingestion and Team Intelligence

**Rationale:** Sleeper ingestion is the root dependency for all six engines. Nothing works without it. The team direction engine (E3) is the primary value thesis — it must be built and validated before any dependent engine is scaffolded. The snapshot system must be wired here even though retrospective UI comes later; early snapshots cannot be recovered retroactively.

**Delivers:** Working Sleeper sync pipeline, populated DuckDB schema, team scorecard with direction detection, basic React dashboard showing league cards with direction labels and top 3 action items.

**Addresses:** Sleeper ingestion (table stakes), format flags (table stakes), team scorecard sub-scores (table stakes + core differentiator), team direction detection (primary thesis differentiator), roster power ranking (table stakes baseline), basic pick valuations (required for trade evaluator), manual correction support (required before launch), append-only snapshot table (required for Phase 5 retrospectives).

**Avoids:**
- False precision pitfall: output schemas must carry confidence levels and sub-scores from the first endpoint
- Sleeper data gaps pitfall: data health checks and null handling must pass before analysis engines run
- UI complexity creep: dashboard design must surface direction + 3 actions before any sub-score panels

**Phase gate:** Direction labels must be manually reviewed and confirmed against all active leagues before Phase 2 begins. This is a hard gate, not an optional checkpoint.

---

### Phase 2: Trade Intelligence and Manager Profiling

**Rationale:** Trade intelligence (E5) depends on E3 (Team Direction) for direction fit scoring and E4 (Manager Behavior) for counterparty-specific pitch angles. E4 requires meaningful transaction history ingested in Phase 1. Phase 2 should not begin until Phase 1 direction labels are validated — this is the primary pitfall prevention gate.

**Delivers:** Manager dossiers per leaguemate, full trade evaluator (fairness + direction fit + roster fit + manager exploit quality), trade pathing (reroute paths, package alternatives), basic pitch notes per manager.

**Addresses:** Manager dossier (Phase 2 core differentiator — no competitor has this), trade evaluator with direction fit (P1 feature), trade pathing and pitch angles (P1 differentiator).

**Avoids:**
- Over-reliance on KTC consensus: trade evaluator must use league-specific adjusted values as primary signal; KTC is a comparison reference only
- Manager inference from insufficient data: evidence count displayed prominently on every dossier; LOW confidence label enforced below 10-trade threshold

---

### Phase 3: Dynamic Pick Engine and Prospect Tooling

**Rationale:** Dynamic pick valuation (class strength, rebuilder count, standings-based adjustment) is architecturally separate from the direction and trade engines and can be developed in parallel after Phase 2 is validated. The rookie board and package builder depend on pick valuations being accurate — they come after the dynamic engine, not before.

**Delivers:** Dynamic pick engine with standings-aware valuation, format-aware rookie board with tier overlays, package builder with manager-specific opening offers, pick timing recommendations (sell/hold/use), portfolio exposure dashboard with correlated risk flags.

**Addresses:** Dynamic pick engine (P2 feature, key differentiator), rookie board (P2 feature), package builder with manager-specific offers (P2 — highest-leverage trade output), portfolio exposure dashboard (P2 — multi-league managers).

**Avoids:**
- Static pick valuation pitfall: pick values must be computed from current standings at evaluation time; no stored round-to-value mapping used as primary source
- This is the first phase where the `research-phase` command during planning would add value — the dynamic pick engine algorithm has domain-specific nuances worth deeper research before implementation

---

### Phase 4: Historical Prospect Lab

**Rationale:** The historical prospect database requires significant data engineering (ETL from NFL draft history sources like NFLverse/nfl-data-py) before any model can be trained. This phase is high research value but structurally deferred — the backtested hit-rate models are meaningless until the base tool has been validated as useful in Phases 1–3. Building this before validating product-market fit is the wrong investment order.

**Delivers:** Historical prospect database (10+ years, position models), archetype clustering and historical comp scoring, hit-rate buckets with confidence bands by position and draft capital tier, scikit-learn feature models.

**Addresses:** Historical prospect database (P3 — deferred), backtested hit-rate models (P3), archetype clustering and comps (P3).

**Avoids:**
- Prospect model overfitting: sample size audit per position before model selection; time-based train/test splits (not random); hit rates on held-out window must match expectations; simpler threshold models before ML models

**Research flag:** Phase 4 needs `research-phase` before implementation. The ML modeling approach (sample size constraints, feature selection, backtesting methodology) has domain-specific complexity. The ETL from NFLverse also needs API investigation.

---

### Phase 5: Retrospectives and Calibration

**Rationale:** Recommendation retrospectives require Phase 1–3 to have been running long enough to produce outcomes worth grading. The append-only snapshot table wired in Phase 1 makes this phase mechanical — the data is already there. This phase closes the trust loop: showing that direction labels were calibrated and prospect tiers hit builds long-term confidence in the system's outputs.

**Delivers:** Season-over-season retrospective dashboard (were direction labels right?), prospect tier outcome grading, manager behavior trend persistence across seasons, calibration tooling to tune engine weights based on historical accuracy.

**Addresses:** Recommendation retrospectives (P3 — future consideration), manager behavior trend persistence (P3 — deferred).

---

### Phase Ordering Rationale

- **Ingestion before analysis:** Every engine depends on the Sleeper sync pipeline. The adapter and repository layers must exist before any engine is scaffolded.
- **Direction before trade:** E5 (Trade Pathing) uses direction fit as a primary scoring dimension. Building the trade evaluator before the direction engine is validated produces a system that is precisely wrong.
- **Validation gate between Phase 1 and Phase 2:** The pitfalls research identifies direction miscalibration discovered after Phase 2 as a HIGH recovery cost. The gate is cheap; the recovery is not.
- **Pick engine before package builder:** The package builder's counterparty-specific offers depend on knowing accurate pick values. Dynamic pick valuations must exist first.
- **Historical lab after validation:** The prospect database is high ceiling but requires the core product to be validated as useful before the data engineering investment is made.
- **Snapshot table in Phase 1, retrospective UI in Phase 5:** Append-only snapshots cost almost nothing to write. Missing early snapshots cannot be recovered.

---

### Research Flags

Phases likely needing `/gsd:research-phase` during planning:
- **Phase 3:** Dynamic pick valuation algorithm — the formula for adjusting pick values based on class strength, league rebuilder count, and calendar timing has domain-specific nuance; research into dynasty community methodology and existing models before specifying the algorithm
- **Phase 4:** Prospect model methodology and NFLverse ETL — ML model selection with small sample sizes is non-trivial; the data engineering pipeline from external draft history sources needs API investigation

Phases with well-documented patterns (can skip research-phase):
- **Phase 1:** FastAPI + DuckDB + Sleeper ingest is a well-documented stack with multiple production examples; adapter and repository patterns are standard; no research needed
- **Phase 2:** Trade evaluator and manager profiling patterns are straightforward once Phase 1 domain models exist; implementation complexity is in the engine logic, not unfamiliar technology
- **Phase 5:** Retrospective dashboard is a read-only aggregation layer over existing snapshot data; no novel patterns required

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core stack verified via PyPI, npm, and official docs; version compatibility matrix verified; alternatives analysis is thorough and sourced |
| Features | HIGH (architecture/landscape), MEDIUM (gap analysis) | Competitor feature sets verified from official sources; gap analysis confirmed by indirect evidence; competitor internal roadmaps are LOW confidence and excluded from recommendations |
| Architecture | HIGH (platform specifics and engine decoupling), MEDIUM (schema patterns) | Engine isolation and adapter patterns are established; schema patterns are reasonable but SQLite mentioned in architecture file where DuckDB is the confirmed stack choice — see gap note below |
| Pitfalls | HIGH | Domain-specific pitfalls verified across multiple sources; engineering pitfalls from established sports analytics ML literature and Sleeper API documentation |

**Overall confidence:** HIGH

### Gaps to Address

- **Schema file references SQLite but stack calls for DuckDB:** The ARCHITECTURE.md schema examples use SQLite DDL syntax (e.g., `datetime('now')`) and reference SQLite as the data layer. The STACK.md research is definitive that DuckDB is the correct choice for this workload. During Phase 1 implementation, the schema must be written for DuckDB, and DuckDB-specific DDL patterns should be verified against the DuckDB 1.5.0 docs. The architecture file's SQLite references are the template pattern, not the implementation target.

- **Player stats reconstruction approach:** Sleeper's player stats endpoint is deprecated. The PITFALLS.md confirms this; ARCHITECTURE.md does not address how scoring history should be reconstructed. Phase 1 must specify whether matchup-based score reconstruction is feasible for the team scorecard sub-scores or whether the scoring history dependency is scoped out of Phase 1 entirely.

- **E4 graceful degradation threshold:** The architecture notes that E4 (Manager Behavior) "degrades gracefully when data is sparse" but does not define the threshold. PITFALLS.md recommends 10 trades as the LOW confidence boundary. This should be formalized as a named constant in the engine before Phase 2 begins.

- **External player value seeding:** The system needs a baseline player value to compute the Global Asset Baseline (E1) before any league-specific adjustment is applied. The research confirms that KTC/consensus should not be the foundation, but the alternative (computing values from Sleeper matchup data alone) needs specification during Phase 1 planning. This is the most open technical question in the research.

---

## Sources

### Primary (HIGH confidence)
- PyPI — FastAPI 0.135.1, DuckDB 1.5.0, Polars 1.38.1 (verified 2026-03-11)
- Sleeper API Official Docs — endpoints, rate limits, deprecated stats endpoint, read-only scope: https://docs.sleeper.com/
- React official blog — React 19.2 stable: https://react.dev/blog/2025/10/01/react-19-2
- Vite official blog — Vite 6.0 release: https://vite.dev/blog/announcing-vite6
- TanStack Query docs: https://tanstack.com/query/latest
- SQLModel docs: https://sqlmodel.tiangolo.com/
- KeepTradeCut FAQ — confirms scoring limitation and crowdsourced algorithm: https://keeptradecut.com/frequently-asked-questions

### Secondary (MEDIUM confidence)
- JetBrains — Django vs Flask vs FastAPI (February 2025): https://blog.jetbrains.com/pycharm/2025/02/django-flask-fastapi/
- MotherDuck — DuckDB vs SQLite comparison: https://motherduck.com/learn-more/duckdb-vs-sqlite-databases/
- Architecting a Fantasy Football Trade Analyzer: https://dev.to/ffteamnames/architecting-a-fantasy-football-trade-analyzer-apis-algorithms-and-avoiding-bias-1a76
- APScheduler + FastAPI integration: https://rajansahu713.medium.com/implementing-background-job-scheduling-in-fastapi-with-apscheduler-6f5fdabf3186
- Footballguys — Dynasty Investor: Rookie Pick Valuation (2024): https://www.footballguys.com/article/2024-dynasty-investor-rookie-pick-valuation
- Northwestern Sports Analytics — ML for NFL prospect success (2024): https://sites.northwestern.edu/nusportsanalytics/2024/03/29/using-machine-learning-and-college-profiles-to-predict-nfl-success/
- DynastyNerds Tools page: https://www.dynastynerds.com/dynasty-tools/
- StatChasers Rookie Hit Rates: https://statchasers.com/rookie-hit-rates/
- Dynasty Daddy portfolio feature: https://dynasty-daddy.com/fantasy-portfolio
- ffscrapr — confirms Sleeper deprecated player scores endpoint: https://ffscrapr.ffverse.com/
- Machine Learning for sports betting — calibration vs. accuracy (ScienceDirect 2024)
- Methodology and evaluation in sports analytics — ML (Springer Nature 2024)

### Tertiary (LOW confidence)
- Fantasy Sports Engine Architecture Core Modules (Arka Softwares): https://www.arkasoftwares.com/blog/fantasy-sports-engine-architecture-core-modules/
- Competitor internal roadmaps — excluded from recommendations; feature sets only, verified from public tool pages

---

*Research completed: 2026-03-11*
*Ready for roadmap: yes*
