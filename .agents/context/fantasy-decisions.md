---
id: fantasy.decision-grounding
title: Repository-Grounded Fantasy Decisions
tier: project
status: active
last_reviewed: 2026-08-03
applies_when:
  - fantasy_advice
  - roster_decision
  - trade_decision
  - pick_decision
---

# Repository-Grounded Fantasy Decisions

Use the local DuckDB as the primary source for league-specific facts. A generic
market ranking does not establish the user's league, ownership, format, roster,
pick inventory, standings, or competitive direction.

## Required workflow

1. Run the record-by-default advice command from `backend` whenever a decision
   packet will be presented to the user:

   ```bash
   uv run fantasy-advise --question "Would you trade Joe Burrow for straight picks?" --json
   ```

   Advice schedules an unresolved follow-up 30 days later by default. Use
   `--follow-up-days` when the decision has a different evaluation horizon.

   Use `uv run fantasy-context --player "Joe Burrow" --json` only for read-only
   lookup when no advice will be presented. It never records lifecycle events.
2. Resolve the portfolio owner through `FANTASY_PORTFOLIO_OWNER_ID` or
   `FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME`. Do not silently select an unrelated
   roster when owner configuration is missing or unmatched.
3. Read `decision_packets[]`, not just the raw roster snapshot. The stable
   packet contract is `decision-packet/1.0` and composes format, roster, picks,
   standings, score semantics, persisted lineup/player-value evidence, market
   inputs, semantic data health, and calibration truth.
4. Ground the answer in each matching owned league's evidence. Treat
   `team_scorecard.semantics` as authoritative for score direction: fragility
   and age risk are lower-is-better, while the composite is explicitly
   beneficial team quality.
5. State stale, missing, degraded, or integrity-blocked fields. A completed
   ingest is transport freshness, not proof that the payload is valid. Use
   `data_health.scoring_season`; never combine seasons implicitly.
6. If `interpretation.status` is `underspecified` or `partially_specified`, ask
   only for the fields in `missing_details`. Do not turn “straight picks” into
   an invented package or a binary accept/decline call.
7. Do not present confidence as calibrated unless
   `evidence.calibration.status` is `available` with a non-zero sample.
8. Do not replace a required live
   ingest with external rankings or an older snapshot.
9. Use current external market information only after local ownership and league
   context are established. Label market evidence separately from repo facts.

## Trade reasoning preflight

Before proposing a trade package, build a short constraints-and-scenarios ledger
from the user's messages and the owned roster. Keep it active for the rest of
the conversation; a user correction invalidates any downstream recommendation
that relied on the corrected premise.

- Record explicit needs, dislikes, exclusions, and exposure concerns separately
  from generic market value. Do not reintroduce an excluded player, position, or
  correlated team/offense as a fallback.
- Model the lineup both before and after material return/role changes. Count
  starters by position and flex, then identify the first, second, and taxi
  contingency at the traded position. A bench player is not automatically
  surplus, and a projected starter is not automatically required depth.
- Model the counterparty's before-and-after roster and incentive as well. Count
  the relevant position before and after the trade; do not assume a manager
  will exchange a needed starter for a lateral move. If the deal leaves them
  at the same depth, require a clear tier upgrade or another concrete benefit,
  otherwise discard the package.
- Evaluate the received asset for actual role, role certainty, age/upside,
  injury/competition risk, and team/offense correlation. Do not use a market
  ranking to fill an unresolved fit gap.
- Compare every incoming and outgoing asset directionally before proposing a
  package. Do not ask for a more valuable player plus an additional asset in
  exchange for a less valuable player unless the countervailing payment is
  explicit and justified.
- Separate the recommendation into one concrete counter, a clear hold/decline
  condition, and any lower-confidence alternative. If no candidate passes the
  user's constraints, give a polite decline instead of asking the initiating
  manager to invent the counter.
- Make every actionable recommendation concrete: name the exact player or
  pick, manager/team or waiver context, opening offer, maximum price or
  walk-away point, and why it fits the modeled lineup. "Target a young RB"
  or "add a TE2" is incomplete; if no named target passes, say that directly.
- After each correction, restate the updated roster model and recompute the
  package; do not carry forward a prior target or conclusion by inertia.

## Capability and feedback truth

Inspect runtime availability before relying on an optional evidence domain:

```bash
uv run python -m fantasy.capabilities --json
```

The manifest distinguishes implementation (`provider: native`) from live data
availability (`runtime_state`). `degraded`, `unavailable`, and
`verification_required` are not passing states. Market capability evidence
includes the latest successful refresh and the latest attempt, including the
format profile, coverage, and failure detail.

When the user later supplies the action taken or outcome, append it by the
persisted decision ID; no temporary packet file is required:

```bash
uv run python -m fantasy.decision.feedback_cli \
  --decision-id 75941ec89ffb4c3ea623 --event rejected \
  --notes "Offer stayed generic"

uv run python -m fantasy.decision.feedback_cli \
  --decision-id 75941ec89ffb4c3ea623 --event outcome \
  --outcome recommendation_correct --outcome-score 1
```

List the unresolved queue without mutating it. `--due-only` is evaluated against
the persisted follow-up timestamp:

```bash
uv run fantasy-feedback --list-open --due-only
```

Action events can reschedule the next review explicitly:

```bash
uv run fantasy-feedback --decision-id 75941ec89ffb4c3ea623 \
  --event accepted --follow-up-at 2026-12-01T12:00:00Z
```

Feedback is append-only. Run calibration only after enough labeled outcomes exist;
the default evidence floor is 20 decisions and the command exits non-zero below it:

```bash
uv run python -m fantasy.decision.calibration_cli --season 2026
```

Run the complete repository and live-capability boundary with one command:

```bash
uv run fantasy-agent-check --json
```

Its `overall_state` and individual checks retain `passed`, `degraded`,
`unavailable`, and `failed` as distinct states. Exit codes are respectively
0, 2, 3, and 1; degraded data is never reported as a passing validation.

## Question boundary

Consult the repository for questions about trades, starts/sits, adds/drops,
waivers, picks, roster construction, standings, league settings, or team
direction. Generic NFL rules, history, or trivia do not require private league
context unless the user connects them to a roster decision.

## Safety and freshness

- The context command opens `data/fantasy.duckdb` read-only and never mutates
  data. The advice command builds through that read-only boundary and then uses
  a separate append-only feedback connection for presentation evidence.
- Its default freshness threshold is 72 hours; override with
  `--stale-after-hours` when the decision requires a tighter window.
- If the relevant league is stale, identify the exact league and request or run
  the documented ingest only when the user has authorized live refresh work.
- Do not expose unrelated managers or leagues when a player query already
  resolves to the user's matching roster.
- `data_health.integrity_status: blocked_by_integrity_failure` excludes the
  suspect season from scoring. A prior valid season may be used only when the
  packet labels it `scoring_status: fallback_valid`.
