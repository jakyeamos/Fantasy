---
phase: 08-historical-prospect-lab
plan: "02"
subsystem: ml
tags: [prospects, scikit-learn, backtesting, clustering]
requires:
  - phase: 08-01
    provides: prospect schema, feature builder, and repo foundation
provides:
  - Outcome labeling, position-specific model training, and archetype clustering
affects: [08-03, 08-04, 08-05]
tech-stack:
  added: []
  patterns:
    - walk-forward validation avoids training on future cohorts
    - position-specific model families keep QB separate from RB/WR/TE
key-files:
  created:
    - backend/src/fantasy/prospects/hit_classifier.py
    - backend/src/fantasy/prospects/prospect_model.py
    - backend/src/fantasy/prospects/archetype_clusterer.py
    - backend/tests/prospects/test_hit_classifier.py
    - backend/tests/prospects/test_prospect_model.py
    - backend/tests/prospects/test_archetype_clusterer.py
requirements-completed: [PROS-02, PROS-03]
duration: retroactive
completed: 2026-03-29
---

# 08-02 Summary

Retrospectively documented the shipped Phase 8 modeling layer.

- Added `HitClassifier` for three-bucket historical outcome labeling with minimum-season gating.
- Added `ProspectModel` with position-aware training, walk-forward validation, and probability outputs for current-class prospects.
- Added `ArchetypeClusterer` so the current class can be assigned to learned historical profile buckets instead of hand-authored archetypes.

Verification:

- `cd backend && .venv/bin/pytest tests/prospects -q`
