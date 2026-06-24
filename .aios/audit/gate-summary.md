# Gate Audit Summary

## Current run outcome

- Outcome: warnings only

## Gate decisions

- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- Pre-CR block [error]: Pre-CR blocked the run: coverage result was unavailable.
- AIOS warn [warning]: AIOS warning only: 951 nonblank lines exceeds production source size limit 500; split by responsibility or document an exception
- Pre-CR warn [warning]: Pre-CR warning only: coverage result was unavailable.

## Repeated failure patterns

### Pattern: pre-cr did not produce a passing coverage result
- Seen: 9 times
- Gates: Pre-CR
- Category: process
- Common cause: Pre-CR could not complete its configured readiness workflow.
- Avoid by: Verify Pre-CR setup before relying on the readiness result.
- Example fix: Fix the Pre-CR setup or execution error, then rerun the gate.

## Agent learning lessons

- Split oversized files by responsibility before committing.
- Run focused tests with coverage before committing changed source lines.
- Verify Pre-CR setup before relying on the readiness result.

## Commit-readiness status

- ready with warnings
