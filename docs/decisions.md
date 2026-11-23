# Decisions

Short records of choices that shape the codebase. Add an entry when you make a
choice someone would otherwise have to reverse-engineer, and update an entry
when a decision changes (say what replaced it and why).

## Product

- **What we build**: LaunchAudit audits AI-built web apps before and after
  launch. Input is code (GitHub repo or zip) plus the live URL; output is a
  Launch Report with a verdict (Launch / Fix first / Do not launch), a 0-10
  risk score and every finding with proof. Roadmap: [features.md](features.md).
- **Evidence or it didn't happen**: every finding carries proof (file, line,
  snippet, data-flow trace, HTTP evidence or screenshot). Schemas:
  [api-contract.md](api-contract.md).
- **Scanned code is data**: we never install, run or import code we scan.
- **Live checks need consent**: the live URL is only probed after domain
  ownership is verified, and only through an SSRF-safe client.

## AI providers

- **Order**: Gemini first, Groq as fallback, rule-based fallback when no model
  is available, so a report is always produced.
- **Grounding**: every model claim must quote the code it refers to. The
  model's opinion is stored as `ai_verdict` on the finding, next to the
  engine's own result.
- **Keys** live only in backend env vars read by `app/core/config.py`, never in
  the frontend.

## Stack

| Area | Choice | Why |
|---|---|---|
| Backend | FastAPI, Pydantic v2, pydantic-settings, Python 3.12, uv | Typed, fast to build, OpenAPI for free; 3.12 for broad scanner-tool support |
| Database | Postgres 18 via SQLAlchemy 2 + Alembic, psycopg 3 | Mature ORM with bound parameters and migrations; Postgres 18 over the fresh 19.0 for stability |
| Frontend | Next.js App Router, TypeScript strict, Tailwind CSS v4, shadcn/ui, TanStack Query, Zod, pnpm | Server components by default, owned UI primitives, typed data fetching |
| Tests | pytest; Vitest + React Testing Library; Playwright | One runner per layer |
| Quality | ruff, ESLint, gitleaks, pre-commit, GitHub Actions | Same checks locally and in CI |
| Runtime | Node 26 LTS in CI (24+ supported), Docker Compose for Postgres + backend | |

## Architecture

- **Backend layers (strict MVC)**: router → service → repository. Routers only
  parse input and return schemas; services hold business logic; repositories
  are the only code that touches the database. Details in CONTRIBUTING.md.
- **Config in one place per app**: `backend/app/core/config.py`
  (pydantic-settings) and `frontend/src/lib/env.ts` (Zod). The backend refuses
  to start when required settings are missing or invalid, and error messages
  name the variable but never its value. `DATABASE_URL` is a secret type so it
  cannot leak through logging the settings object.
- **Error format**: every non-2xx response is `{"error": {"code", "message"}}`
  with no stack traces. `HTTPException` details are replaced with generic
  per-code messages; services raise `AppError` subclasses for safe custom
  messages. Malformed JSON is `400 bad_request`; validation failures are
  `422 validation_error` and never echo submitted values.
- **Security middleware**: pure-ASGI security headers and request-size limit
  (default 1 MiB, enforced on Content-Length and on streamed bodies). The
  built-in FastAPI size limit is not used because it answers in plain text.
  CORS is a thin subclass of Starlette's middleware so rejected preflights also
  use the error format. Order, outermost first: security headers, CORS, size
  limit.
- **Auth stub**: a bearer-token check (constant-time compare against
  `API_AUTH_TOKEN`) guards protected routes until real auth lands. With no
  token configured, every protected request is rejected. The token must be at
  least 32 characters, must not be set in production, and the check always
  rejects in production as a second line of defence.
- **No fail-open defaults**: `ENVIRONMENT` has no default, so a deployment
  that forgets it refuses to start instead of silently running in development
  mode (public API docs, no HSTS).
- **App factory**: the backend runs with
  `uvicorn app.main:create_app --factory`; there is no module-level app, so
  importing the code never reads the environment. Tests and the OpenAPI export
  build settings explicitly with `settings_from_values(...)`.
- **Logging**: JSON lines with redaction of Authorization/Bearer values, URL
  credentials, sensitive query parameters and secret-looking keys. SQL
  parameters are hidden.
- **API types**: the backend exports its OpenAPI schema to
  `backend/openapi.json`; the frontend generates `src/types/api.ts` from it
  with openapi-typescript. Both files are committed and CI fails if either is
  stale.
- **Frontend env**: `src/lib/env.ts` is the only module that reads
  `process.env` (an ESLint rule bans it elsewhere). `NEXT_PUBLIC_API_BASE_URL`
  defaults to `http://localhost:8000` in development and test and is required
  for production builds, so a misconfigured deploy fails at build time.
- **Frontend security headers**: CSP with `connect-src` limited to the API
  origin, `frame-ancestors 'none'`, `object-src 'none'`. `'unsafe-inline'` is
  allowed for scripts and styles because the App Router streams inline payload
  scripts and the theme script must run before paint; removing it would need
  per-request nonces, which force every page to render dynamically.
  `'unsafe-eval'` is development-only; HSTS is production-only.
- **Frontend API client**: openapi-fetch over the generated types. Every
  failure becomes an `ApiError` with `code`, `message` and `status`, using the
  backend's codes plus client-side `network_error`, `timeout`, `aborted`,
  `http_error` and `invalid_response`.
- **UI kit**: shadcn/ui on its current default (Base UI primitives, `cn`
  class merger from the shadcn-ui org). Only the primitives in use are kept.
- **Design system**: calm security-instrument look: cool paper and deep petrol
  ink, no gradients or glass. Schibsted Grotesk for UI, IBM Plex Mono for code,
  paths and scores. Severity (Critical/High/Medium/Low) and verdict
  (Launch/Fix first/Do not launch) tokens in light and dark mode, all
  WCAG AA; badges always pair colour with a word and a distinct shape or icon.
  Tokens live in `frontend/src/app/globals.css`.
- **Containers**: the backend image runs as a non-root user (uid 10001) with a
  read-only filesystem in Compose; ports bind to 127.0.0.1 only.
- **Supply chain pinning**: Docker base images are pinned by digest, GitHub
  Actions by commit SHA, pre-commit hooks by commit SHA, and the gitleaks
  binary in CI is verified against its release checksum. Tags stay alongside
  as comments for readability.

## Workflow

- **Branches**: one feature = one branch, `feat/<slug>` (also `fix/<slug>`,
  `chore/<slug>`), created from the latest `main`.
- **Commits**: small Conventional Commits (`feat(backend): ...`,
  `fix(frontend): ...`, `docs: ...`, `chore: ...`, `ci: ...`, `test: ...`).
- **Main is protected by convention**: push only feature branches; never push
  to `main`, force-push or merge your own PR. Changes land through a PR with
  one approval and passing CI. The only direct commit to `main` was the
  initial repository seed, made because the repository was empty.
- **Definition of done**: tests with every feature, all lint/typecheck/test
  commands pass locally, docs updated in the same PR.
- **No attribution**: commit messages carry no `Co-Authored-By` or other
  trailers, and commits, PR titles, bodies and comments carry no "Generated
  with ..." lines. Commits are authored by the developer's own identity.

## Coding-assistant setup

- **Shared, not local**: `CLAUDE.md`, `.claude/` (agents, skills, settings) and
  `.mcp.json` are committed so every developer's assistant follows the same
  rules, decisions and subagents. Personal overrides go in
  `.claude/settings.local.json` and `CLAUDE.local.md`, which are git-ignored.
- **Settings**: `.claude/settings.json` turns commit and PR attribution off
  (`attribution.commit` / `attribution.pr` set to empty, plus the legacy
  `includeCoAuthoredBy: false`), denies reading or editing real `.env` files
  (only `.env.example` is allowed), and pre-allows routine pnpm, uv, pytest,
  ruff and local git commands. Escape hatches stay denied: `git add -f`,
  `git commit --no-verify`, force-push, `pnpm dlx`, `uv pip` and `uvx`.
- **Subagents**: `backend-dev`, `frontend-dev`, `test-writer`, `ui-reviewer`,
  `security-reviewer` (read-only).
- **Skills**: `frontend-design` for all UI work; Supabase skills for the
  vibe-coding checks. Pinned in `skills-lock.json`.
- **MCP**: Context7 for current library docs; no keys required.

## Tooling

- **pnpm is installed with npm, not corepack**: pnpm 12 ships as a native
  executable that corepack cannot launch, and Node 25+ no longer bundles
  corepack. `packageManager` in `frontend/package.json` still pins the version.
- **Secrets scanning twice**: gitleaks runs as a pre-commit hook (the
  installed binary, on staged changes) and over the full git history in CI, so
  a leaked key is caught before it reaches GitHub and again if a hook was
  skipped. Fake key-shaped test values carry an inline `gitleaks:allow`;
  fixture scenario folders are allowlisted in `.gitleaks.toml`.
- **TypeScript 6.0, not 7.0**: TS 7 builds and typechecks, but
  typescript-eslint (via eslint-config-next) does not support it yet. Move to
  7 when typescript-eslint does.
- **Test client deprecation**: Starlette 1.10 warns that its test client
  should use `httpx2` instead of `httpx`. Tests still pass on `httpx`; switching
  is an open dependency decision.
- **Line endings**: `.gitattributes` forces LF so Windows and macOS checkouts
  produce identical diffs.
