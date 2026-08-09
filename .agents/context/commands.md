# Commands

- `cd backend && .venv/bin/pytest`
- `cd backend && uv run python -m fantasy.agent_context --question "<question>" --json`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm typecheck`
- `cd frontend && pnpm build`
- `cd frontend && pnpm dev`

Run the strongest relevant subset before completion and report skipped or failing commands.
