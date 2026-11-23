# Contributing to LaunchAudit

LaunchAudit audits web apps before and after launch. A user adds code (a GitHub
repo or a zip) plus the live URL, presses **Run**, and gets a **Launch Report**:
a verdict (Launch / Fix first / Do not launch), a 0-10 risk score, and every
problem with proof (file, line, snippet, data-flow trace, HTTP evidence or a
screenshot).

This guide is the source of truth for how the codebase is organised and how we
work. Read it before your first change.

## Folder map

```
backend/                 FastAPI API (Python 3.12, uv)
  app/main.py            App factory: middleware, routers, error handlers
  app/api/routers/       Controllers: HTTP in/out only, no business logic
  app/api/deps.py        Shared FastAPI dependencies (auth, DB session)
  app/schemas/           Pydantic v2 request/response models
  app/models/            SQLAlchemy 2 ORM models
  app/repositories/      The only layer that touches the database
  app/services/          Business logic (scan, live, journeys, ai, report)
  app/core/              config, security, errors, logging
  alembic/               Database migrations
  tests/                 pytest
frontend/                Next.js App Router (TypeScript strict, pnpm)
  src/app/               Routes and views
  src/components/ui/     shadcn/ui primitives (generated, lightly themed)
  src/components/        Product components
  src/lib/api/           Typed API client
  src/lib/               Utilities, env validation (env.ts)
  src/hooks/             React hooks (TanStack Query wrappers)
  src/types/             Generated API types (do not edit by hand)
  tests/unit/            Vitest + React Testing Library
  tests/e2e/             Playwright
docs/                    features.md, api-contract.md, decisions.md
fixtures/                Sample vulnerable apps used by tests (never executed)
```

## Backend layers

Requests flow in one direction: **router → service → repository → database**.

| Layer | Owns | Must not |
|---|---|---|
| `api/routers` | Parse input (Pydantic), call a service, return a schema | Contain logic, touch the DB, call external tools |
| `schemas` | Pydantic models for input/output | Import ORM models into responses directly |
| `services` | Business rules, orchestration, calling scanners | Build SQL, read `os.environ` |
| `repositories` | All database reads/writes via SQLAlchemy | Contain business rules |
| `models` | ORM table definitions | Contain logic |
| `core` | Settings, security middleware, error handling, logging | Depend on services |

## Frontend rules

- Server components by default. Add `"use client"` only where interaction or
  hooks are needed.
- All API calls go through the typed client in `src/lib/api`. Types come from
  the backend's OpenAPI schema via `pnpm gen:api`; never hand-write API types.
- Client-side data fetching uses TanStack Query hooks in `src/hooks`.
- Every data view has explicit **loading**, **empty** and **error** states.
- Use the design tokens in `src/app/globals.css` (severity, verdict, type
  scale, spacing). No ad-hoc colours.
- Accessibility: semantic HTML, visible focus, labelled controls, colour is
  never the only signal (severity and verdict badges also carry text).

## Commands

### Backend (run from `backend/`)

| Task | Command |
|---|---|
| Install | `uv sync` |
| Run (dev) | `uv run uvicorn app.main:create_app --factory --reload --port 8000` |
| Lint | `uv run ruff check .` |
| Format check | `uv run ruff format --check .` |
| Test | `uv run pytest` |
| New migration | `uv run alembic revision --autogenerate -m "msg"` |
| Apply migrations | `uv run alembic upgrade head` |
| Export OpenAPI schema | `uv run python -m app.scripts.export_openapi` (writes `openapi.json`) |

After changing any endpoint or schema, export the OpenAPI schema and run
`pnpm gen:api` in `frontend/`, and commit both generated files. CI fails if
they are out of date.

### Frontend (run from `frontend/`)

| Task | Command |
|---|---|
| Install | `pnpm install` |
| Run (dev) | `pnpm dev` |
| Lint | `pnpm lint` |
| Typecheck | `pnpm typecheck` |
| Unit tests | `pnpm test` |
| E2E tests | `pnpm test:e2e` |
| Build | `pnpm build` |
| Regenerate API types | `pnpm gen:api` (reads `backend/openapi.json`) |

### Whole stack

`docker compose up --build` starts Postgres and the backend.

## Security rules

These are non-negotiable. Reviewers block PRs that break them.

1. **Never commit `.env` files or secrets.** Only `.env.example` files with
   variable *names* (and safe defaults) are committed. gitleaks runs in
   pre-commit and CI.
2. **Environment variables are read in one place per app**:
   `backend/app/core/config.py` (pydantic-settings) and
   `frontend/src/lib/env.ts` (Zod). Nowhere else reads `os.environ` or
   `process.env`.
3. **SQL only through SQLAlchemy** with bound parameters. No f-strings or string
   concatenation in queries, including `text()`.
4. **Validate all input**: Pydantic on the backend, Zod on the frontend.
5. **No `shell=True`, `eval`, `exec`** or dynamic imports from user input. Run
   external tools with an argument list and a timeout.
6. **Never execute scanned code.** Uploaded repos and zips are data. Do not
   install their dependencies, run their scripts or import them.
7. **No secrets in `NEXT_PUBLIC_*`** variables. Anything with that prefix is
   shipped to the browser.
8. **CORS origins come from config**, never `*` in production.
9. **Mask secrets** in logs, errors, reports and API responses (show at most a
   short prefix, e.g. `sk_live_••••`).
10. Errors returned to clients use `{"error": {"code", "message"}}` and never
    include stack traces or internal details.
11. Outbound requests to user-supplied URLs (live checks) must go through the
    SSRF-safe client: block private, loopback, link-local and metadata
    addresses, and re-check after redirects.

## Git workflow

- One feature = one branch named `feat/<slug>` (or `fix/<slug>`, `chore/<slug>`),
  created from the latest `main`.
- Plan before coding: write down the files you will touch and the tests you
  will add.
- Every feature ships with tests.
- Small commits using [Conventional Commits](https://www.conventionalcommits.org/):
  `feat(backend): add scan runner`, `fix(frontend): handle empty report`.
- Run **all** checks (lint, typecheck, tests for both apps) before saying a
  change is done or opening a PR.
- Update `docs/` (features status, API contract, decisions) in the same PR.
- Push only your feature branch. Never push to `main`, never force-push, never
  merge your own PR. `main` changes only through reviewed PRs with passing CI.
- Fill in the PR template, including screenshots for UI changes.
