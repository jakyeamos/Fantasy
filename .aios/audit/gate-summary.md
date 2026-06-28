# Gate Audit Summary

## Current run outcome

- Outcome: warnings only

## Gate decisions

- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable. (no file evidence)
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable. (no file evidence)
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable. (no file evidence)
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable. (no file evidence)
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable. (no file evidence)
- AIOS warn [warning]: AIOS warning only: 951 nonblank lines exceeds production source size limit 500; split by responsibility or document an exception (frontend/src/routes/trades.tsx)
- Pre-CR warn [warning]: Pre-CR warning only: coverage result was unavailable. (no file evidence)
- AIOS warn [warning]: AIOS warning only: 949 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/lineup/hygiene_engine.py)
- AIOS warn [warning]: AIOS warning only: 656 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/actions/command_center.py)
- AIOS warn [warning]: AIOS warning only: 666 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception (backend/src/fantasy/edge_radar/engine.py)

## Repeated failure patterns

- pre-cr did not produce a passing coverage result (9 event(s), Pre-CR, process, fingerprint `f2e4027cb6fbe33827c97e3e`)

## Agent learning lessons

- Verify Pre-CR setup before relying on the readiness result.
- Split oversized files by responsibility before committing.
- Run focused tests with coverage before committing changed source lines.

## Commit-readiness status

- ready only with override
