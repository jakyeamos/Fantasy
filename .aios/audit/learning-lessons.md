# Gate Learning Lessons

## Active repeated failure patterns

### Pattern: pre-cr did not produce a passing coverage result
- Seen: 11 times
- Gates: Pre-CR
- Category: process
- Common cause: Pre-CR could not complete its configured readiness workflow.
- Avoid by: Verify Pre-CR setup before relying on the readiness result.
- Example fix: Fix the Pre-CR setup or execution error, then rerun the gate.

### Pattern: source file exceeded size limit
- Seen: 3 times
- Gates: AIOS
- Category: maintainability
- Common cause: A staged change violated a deterministic commit quality rule.
- Avoid by: Split oversized files by responsibility before committing.
- Example fix: 951 nonblank lines exceeds production source size limit 500; split by responsibility or document an exception

### Pattern: source file exceeded size limit
- Seen: 2 times
- Gates: AIOS
- Category: maintainability
- Common cause: A staged change violated a deterministic commit quality rule.
- Avoid by: Split oversized files by responsibility before committing.
- Example fix: 666 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception

### Pattern: production TypeScript used any
- Seen: 18 times
- Gates: AIOS
- Category: typecheck
- Common cause: A staged change violated a deterministic commit quality rule.
- Avoid by: Use concrete TypeScript types before staging production code.
- Example fix: avoid `any` in production TypeScript; use a real type or add `quality-gate: allow any: <reason>`

### Pattern: source file exceeded size limit
- Seen: 3 times
- Gates: AIOS
- Category: maintainability
- Common cause: A staged change violated a deterministic commit quality rule.
- Avoid by: Split oversized files by responsibility before committing.
- Example fix: 880 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception

### Pattern: source file exceeded size limit
- Seen: 2 times
- Gates: AIOS
- Category: maintainability
- Common cause: A staged change violated a deterministic commit quality rule.
- Avoid by: Split oversized files by responsibility before committing.
- Example fix: 1721 nonblank lines exceeds production source size limit 600; split by responsibility or document an exception

## Current repo-specific rules learned from gate history

- Use concrete TypeScript types before staging production code.
- Split oversized files by responsibility before committing.
- Verify Pre-CR setup before relying on the readiness result.
- Run focused tests with coverage before committing changed source lines.

## High-priority agent reminders

- Verify Pre-CR setup before relying on the readiness result.
