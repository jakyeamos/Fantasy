---
phase: 21-player-value-trends-and-market-inefficiency-trade-suggestions
plan: "05"
subsystem: full-stack-contract
tags: [fastapi, router, tanstack-query, typescript]
completed: 2026-03-31
---

# 21-05 Summary

- Added `GET /opportunities`, registered the router in `main.py`, and covered the route with backend tests.
- Wired valuation write-through into `player_trends` so league compute runs keep the trend table current.
- Added TypeScript opportunity types plus `opportunityFeedOptions` for the frontend data layer.
