---
phase: 01-sleeper-ingestion
plan: "02"
subsystem: repository
tags: [duckdb, nfl_data_py, repository, upsert]
requires:
  - phase: 01-01
    provides: domain model Pydantic models
provides:
  - LeagueRepo with upsert methods for leagues, rosters, standings, traded_picks, transactions
  - NflDataPyLoader for weekly stats and fantasy point reconstruction
  - Alembic migrations 002 (player_stats_weekly) and 003 (player_adp_baseline)
affects: [01-03, 01-04, 02, 06]
tech-stack:
  added: [nfl_data_py]
  patterns: [raw SQL DuckDB upserts via INSERT OR REPLACE / ON CONFLICT DO UPDATE]
key-files:
  created:
    - backend/src/fantasy/repositories/league_repo.py
    - backend/src/fantasy/ingestion/nfl_data_loader.py
    - backend/alembic/versions/002_add_player_stats_weekly.py
    - backend/alembic/versions/003_add_adp_baseline.py
  modified:
    - backend/tests/test_league_repo.py
key-decisions:
  - "nfl_data_py over Sleeper deprecated stats endpoint for scoring history"
  - "Fantasy points reconstructed from raw stat lines using each league's actual scoring_settings"
requirements-completed: [INGEST-03, INGEST-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 01-02: Repository Layer Summary

**DuckDB upsert layer and nfl_data_py stats loader with fantasy point reconstruction.**

## Accomplishments

- `LeagueRepo` with idempotent upsert for all 5 core entity types (tested)
- `NflDataPyLoader` maps Sleeper scoring keys to nflverse column names, computes fantasy points per player/week
- ADP baseline loader from CSV

## Known Quality Gaps

- `load_adp_baseline()` still requires CSVs pre-processed with Sleeper player IDs. The loader now fails fast instead of silently loading unusable rows, but name-only CSVs remain unsupported.
