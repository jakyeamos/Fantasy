# fantasy-frontend

Vite/TanStack Router frontend for the Fantasy project user interface.

## Scope

This README documents the `frontend` subproject inside `Fantasy`.
It is marked private in `package.json` and is intended for workspace use rather than standalone publishing.

## Repository Layout

- `.gitignore` - project file.
- `.tanstack/` - project directory.
- `index.html` - project file.
- `package.json` - JavaScript package metadata and scripts.
- `src/` - source code and package internals.
- `tsconfig.app.json` - project file.
- `tsconfig.json` - project file.
- `tsconfig.node.json` - project file.
- `vite.config.ts` - project file.

## Common Commands

- `pnpm dev` - `vite`
- `pnpm build` - `tsc --noEmit && vite build`
- `pnpm format` - checked Prettier formatting
- `pnpm browser:smoke` - bounded Playwright route, interaction, and state smoke
- `pnpm preview` - `vite preview`
- `pnpm format` - enforce Prettier on files added or changed after the recorded legacy baseline
- `pnpm format:baseline` - explicitly refresh reviewed legacy hashes after formatter configuration or intentional normalization changes

## Development Notes

Runtime dependencies include `@tanstack/react-query`, `@tanstack/react-query-devtools`, `@tanstack/react-router`, `clsx`, `lucide-react`, `react`, `react-dom`, `tailwind-merge`.
Use `pnpm` from the containing workspace to install dependencies and run scripts.

## Verification

Run `pnpm typecheck`, `pnpm audit:dead-code`, `pnpm format`, and `pnpm build`.
The formatting baseline does not declare legacy files formatted; it prevents
unchanged legacy style from blocking work while requiring every later change
or new file to satisfy the pinned Prettier contract.

The browser smoke harness uses explicit DOM readiness rather than Vite's
persistent-HMR `networkidle` state. It also checks empty, stale, degraded, and
error opportunity fixtures through `?smokeState=` routes.
