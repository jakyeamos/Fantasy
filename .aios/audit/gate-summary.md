# Gate Audit Summary

## Current run outcome

- Outcome: warnings only

## Gate decisions

- AIOS warn [warning]: AIOS warning only: avoid `any` in production TypeScript; use a real type or add `quality-gate: allow any: <reason>` (frontend/src/routeTree.gen.ts)
- AIOS warn [warning]: AIOS warning only: avoid `any` in production TypeScript; use a real type or add `quality-gate: allow any: <reason>` (frontend/src/routeTree.gen.ts)
- AIOS warn [warning]: AIOS warning only: 880 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/lineup/lineup_engine.py)
- AIOS warn [warning]: AIOS warning only: 1721 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/routers/dashboard.py)
- AIOS warn [warning]: AIOS warning only: 1735 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/routers/dashboard.py)
- AIOS warn [warning]: AIOS warning only: 893 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/lineup/lineup_engine.py)
- AIOS warn [warning]: AIOS warning only: 904 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/lineup/lineup_engine.py)
- Pre-CR warn [warning]: Pre-CR warning only: coverage result was unavailable. (no file evidence)
- Pre-CR warn [warning]: Pre-CR warning only: coverage result was unavailable. (no file evidence)
- AIOS warn [warning]: AIOS warning only: 624 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/edge_radar/engine.py)

## Repeated failure patterns

- pre-cr did not produce a passing coverage result (11 event(s), Pre-CR, process, fingerprint `f2e4027cb6fbe33827c97e3e`)
- source file exceeded size limit (3 event(s), AIOS, maintainability, fingerprint `9ffce0839b0d9e869d384e5a`)
- source file exceeded size limit (2 event(s), AIOS, maintainability, fingerprint `c305dd3a4ecd9cd26abf9303`)
- production TypeScript used any (18 event(s), AIOS, typecheck, fingerprint `3e50dfe1f5789ff8578e6f38`)
- source file exceeded size limit (3 event(s), AIOS, maintainability, fingerprint `0123851b9810d707646556f7`)
- source file exceeded size limit (2 event(s), AIOS, maintainability, fingerprint `54f4da41615a38921bc49de7`)

## Agent learning lessons

- Use concrete TypeScript types before staging production code.
- Split oversized files by responsibility before committing.
- Verify Pre-CR setup before relying on the readiness result.
- Run focused tests with coverage before committing changed source lines.

## Commit-readiness status

- ready only with override
