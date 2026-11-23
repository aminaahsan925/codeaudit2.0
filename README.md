# LaunchAudit

LaunchAudit audits AI-built web apps before and after launch. Add your code (a
GitHub repo or a zip) and the live URL, press **Run**, and get a **Launch
Report**: a verdict (Launch / Fix first / Do not launch), a 0-10 risk score, and
every problem with proof — file, line, snippet, data-flow trace, HTTP evidence
or a screenshot.

> Status: project foundation. See [docs/features.md](docs/features.md) for the
> roadmap and [CONTRIBUTING.md](CONTRIBUTING.md) for how we work.

## Stack

| Part | Tech |
|---|---|
| Frontend | Next.js (App Router), TypeScript strict, Tailwind CSS, shadcn/ui, TanStack Query, Zod, pnpm |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2 + Alembic, uv |
| Database | Postgres (Docker) |
| Quality | ruff, pytest, ESLint, Vitest + React Testing Library, Playwright, gitleaks, pre-commit |

## Prerequisites

| Tool | Version |
|---|---|
| Git | 2.40+ |
| Node.js | 24 LTS or newer (CI uses 26) |
| pnpm | 12 (install with npm, see below) |
| Python | 3.12 (uv installs it for you) |
| uv | 0.11+ |
| Docker Desktop | latest |
| gitleaks, pre-commit | latest |

### Windows (PowerShell)

```powershell
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id astral-sh.uv -e
winget install --id Docker.DockerDesktop -e
winget install --id Gitleaks.Gitleaks -e --scope user
npm install -g pnpm@latest
uv python install 3.12
uv tool install pre-commit
```

Open a new terminal afterwards so the updated `PATH` is picked up, and start
Docker Desktop once to finish its setup (it may ask to enable WSL 2).

### macOS (Homebrew)

```bash
brew install git node uv gitleaks pre-commit
brew install --cask docker
npm install -g pnpm@latest
uv python install 3.12
```

Start Docker Desktop once from Applications to finish its setup.

## Getting started

```bash
git clone https://github.com/aminaahsan925/codeaudit2.0.git
cd codeaudit2.0
pre-commit install
```

Copy each `.env.example` to `.env` (root, `backend/`, `frontend/`) and fill in
the values. Never commit `.env` files.

### Run the backend

```bash
cd backend
uv sync
uv run uvicorn app.main:create_app --factory --reload --port 8000
```

Health check: <http://localhost:8000/api/health>. API docs (development only):
<http://localhost:8000/api/docs>.

### Run the frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open <http://localhost:3000>. The header badge shows whether the backend is
reachable.

### Run Postgres + backend with Docker

```bash
docker compose up --build
```

## Checks

Run all of these before opening a PR (CI runs the same).

```bash
# backend/
uv run ruff check .
uv run ruff format --check .
uv run pytest

# frontend/
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm exec playwright install chromium   # first time only
pnpm test:e2e

# repo root
pre-commit run --all-files
```

## Repository layout

```
backend/    FastAPI API (routers → services → repositories)
frontend/   Next.js app
docs/       Features, API contract, decisions
fixtures/   Sample vulnerable apps for scanner tests (never executed)
```

Details for each layer are in [CONTRIBUTING.md](CONTRIBUTING.md).
