---
phase: 04-manager-profiling
plan: "04"
subsystem: frontend
tags: [dossier, tabs, trade-history, pitch-angles]
requires:
  - phase: 04-03
    provides: managers list route
provides:
  - league.$leagueId.managers.$managerId route (dossier page)
  - Three-tab view: Overview, Trade History, Pitch Angles
  - DossierOverviewTab: exploitation classification, roster summary, aggregate trade stats
  - DossierTradeHistoryTab: chronological trade log with value deltas
  - DossierPitchAnglesTab: ranked deal archetypes with send/avoid guidance
affects: [05]
tech-stack:
  added: []
  patterns: [three-tab dossier layout with TanStack Query per tab]
key-files:
  created:
    - frontend/src/routes/league.$leagueId.managers.$managerId.tsx
    - frontend/src/components/DossierOverviewTab.tsx
    - frontend/src/components/DossierTradeHistoryTab.tsx
    - frontend/src/components/DossierPitchAnglesTab.tsx
requirements-completed: [MGR-01, MGR-02, MGR-03, MGR-04]
duration: retroactive
completed: 2026-03-22
---

# Phase 04-04: Manager Dossier Frontend Summary

**Three-tab manager dossier with overview, trade history, and pitch angles.**
