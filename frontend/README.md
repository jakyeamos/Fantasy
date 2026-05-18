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
- `pnpm preview` - `vite preview`

## Development Notes

Runtime dependencies include `@tanstack/react-query`, `@tanstack/react-query-devtools`, `@tanstack/react-router`, `clsx`, `lucide-react`, `react`, `react-dom`, `tailwind-merge`.
Use `pnpm` from the containing workspace to install dependencies and run scripts.

## Verification

There is no local verification command documented in this directory yet; use the parent workspace checks when available.
