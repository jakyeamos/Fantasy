---
phase: 07-rookie-board-draft-room
plan: "02"
subsystem: backend
tags: [rookie-engine, tiers, class-strength]
requires:
  - phase: 07-01
    provides: rookie models, constants, and repository access
provides:
  - RookieEngine board computation pipeline
  - Format-aware scoring for QB, pass-catcher, and TEP adjustments
  - Gap-based tiering, archetype labels, and risk bands
  - Class-strength signal and slot-availability estimation
affects: [07-03, 07-04, 06]
tech-stack:
  added: []
  patterns:
    - board computation always refreshes cache and draft tendencies together
    - slot availability stored per player per formatted slot key
key-files:
  created: []
  modified:
    - backend/src/fantasy/rookie/rookie_engine.py
    - backend/tests/rookie/test_rookie_engine.py
requirements-completed: [PICK-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 07-02: Rookie Engine Summary

**Implemented the rookie board engine with format-aware scoring, dynamic tier breaks, archetype/risk labeling, and class-strength calculation for downstream pick valuation.**

## Verification

- `backend/tests/rookie/test_rookie_engine.py` passes
