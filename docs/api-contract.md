# API contract

Base URL (local): `http://localhost:8000`. All endpoints live under `/api`.
OpenAPI schema: `GET /api/openapi.json` (interactive docs at `/api/docs` outside production).
Frontend types are generated from the OpenAPI schema with `pnpm gen:api`; this
document describes intent, the OpenAPI schema is the machine-readable truth.

## Conventions

- JSON only, `snake_case` fields, timestamps in ISO 8601 UTC (`2026-11-23T18:00:00Z`).
- IDs are UUID v4 strings.
- Request bodies larger than `MAX_REQUEST_BYTES` (default 10 MB) are rejected with `413`.
- Authenticated endpoints expect `Authorization: Bearer <token>`.

### Error format

Every non-2xx response has this shape. No stack traces or internal details are ever included.

```json
{ "error": { "code": "not_found", "message": "Resource not found." } }
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `bad_request` | Malformed request |
| 401 | `unauthorized` | Missing or invalid bearer token |
| 403 | `forbidden` | Authenticated but not allowed |
| 404 | `not_found` | Unknown route or resource |
| 405 | `method_not_allowed` | Wrong HTTP method |
| 413 | `payload_too_large` | Body over the size limit |
| 422 | `validation_error` | Body/query failed validation |
| 429 | `rate_limited` | Too many audit runs in the last hour |
| 500 | `internal_error` | Unexpected server error (logged server-side) |

## Endpoints (foundation)

### `GET /api/health`

Public liveness check. Does not touch the database.

```json
{ "status": "ok", "version": "0.1.0" }
```

### `GET /api/auth/me`

Auth stub. Returns `401 unauthorized` without a valid bearer token. In
development a single token from `API_AUTH_TOKEN` is accepted (compared in
constant time); if it is unset, every request is rejected. Real auth replaces
this later.

```json
{ "subject": "dev" }
```

## Domain schemas

### Finding

One problem found by any engine, with the evidence that proves it.

| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `rule_id` | string | Engine rule, e.g. `python.lang.security.audit.subprocess-shell-true` |
| `engine` | enum | `native`, `semgrep`, `gitleaks`, `osv`, `vibe`, `live`, `journey`, `ai` |
| `category` | enum | `secrets`, `injection`, `auth`, `access_control`, `config`, `dependency`, `ssrf`, `xss`, `data_exposure`, `other` |
| `severity` | enum | `critical`, `high`, `medium`, `low` |
| `confidence` | enum | `high`, `medium`, `low` |
| `cwe` | string \| null | e.g. `CWE-78` |
| `title` | string | One-line human summary |
| `file` | string \| null | Repo-relative path (null for live-only findings) |
| `start_line` | int \| null | 1-based |
| `end_line` | int \| null | 1-based, inclusive |
| `snippet` | string \| null | Code excerpt, secrets masked |
| `trace` | TraceStep[] | Data-flow steps from source to sink, may be empty |
| `evidence` | object | Engine-specific proof, see below |
| `ai_verdict` | object \| null | `{ "verdict": "confirmed" \| "likely_false_positive" \| "needs_review", "reason": string, "quoted_code": string }` |
| `fix_guidance` | string \| null | Markdown |
| `status` | enum | `open`, `fixed`, `ignored`, `false_positive` |

`TraceStep`: `{ "file": string, "line": int, "snippet": string, "label": string }`.

`evidence` (all keys optional):

```json
{
  "http": { "method": "GET", "url": "https://app.example.com/api/users", "status": 200,
            "request_headers": {}, "response_headers": {}, "body_excerpt": "..." },
  "screenshot_url": "/api/runs/{run_id}/artifacts/{name}.png",
  "secret_preview": "sk_live_••••",
  "package": { "name": "lodash", "version": "4.17.20", "advisory": "GHSA-..." },
  "notes": "..."
}
```

### AuditRun

| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `project_name` | string | |
| `repo_url` | string \| null | GitHub URL, or null for zip uploads |
| `live_url` | string \| null | Only scanned after domain ownership is verified |
| `status` | enum | `queued`, `running`, `succeeded`, `failed`, `cancelled` |
| `progress` | int | 0-100 |
| `verdict` | enum \| null | `launch`, `fix_first`, `do_not_launch` (null until finished) |
| `risk_score` | number \| null | 0.0-10.0, one decimal |
| `started_at` | datetime \| null | |
| `finished_at` | datetime \| null | |
| `error` | string \| null | Safe, user-facing message when `status = failed` |
| `share_token` | string \| null | Unguessable token for the public share link |
| `is_guest` | boolean | True when the run was created without a bearer token |
| `journey_steps` | object[] \| null | Stored journey steps (`name`, `status`, `screenshot`, `error`) |
| `previous_run_id` | uuid \| null | The run this one reran, if any |
| `domain_verified` | boolean | Whether the live URL's domain was verified for this run |

## Endpoints (audit runs and reports)

### `POST /api/runs`

Multipart form. Creates an audit run and starts the pipeline in the
background. Guest runs need no token; a valid bearer token marks the run
owned (`dev`) so it appears in history. Rate-limited per token or client IP
(`audit_rate_limit_per_hour`, default 10).

Form fields: `project_name` (required), `repo_url` (https github.com URL),
`live_url`, `zip_file` (a `.zip` upload), `journey_email`,
`journey_password`, `domain_token`. At least one of `repo_url` or `zip_file`
is required. Journey credentials are held in memory for the run only and are
never stored. Returns `201` with the `AuditRun` (`status = queued`).

### `GET /api/runs/{run_id}`

Public by id. Returns the `AuditRun` with current `status` and `progress`.

### `GET /api/runs`

Authenticated. Lists runs owned by `dev`, newest first.

### `POST /api/runs/{run_id}/rerun`

Creates a new run from a previous run's inputs (project name, repo URL, live
URL; zip reruns reuse the stored upload). Accepts fresh journey credentials
and a fresh domain token in the body. The new run records `previous_run_id`.
Authenticated when the original run was owned, else public by id. Returns
`201` with the new `AuditRun`.

### `GET /api/runs/{run_id}/artifacts/{name}`

Serves a stored artifact (journey screenshot PNG, uploaded zip). `name` must
be a plain filename; path traversal is rejected with `404`.

### `GET /api/runs/{run_id}/report`

Public by id (run ids are unguessable UUIDs). Returns the full
`ReportResponse`: the run, fix-first findings, severity counts, journey
steps, and for reruns the previous risk score, resolved findings, and score
change.

### `GET /api/reports/shared/{token}`

Public. Returns the `ReportResponse` for the run with that share token.
`404` for an unknown token.

### `GET /api/runs/{run_id}/report.pdf`

Returns the Launch Report as a PDF download. Requires a valid bearer token
or a matching `?token=<share_token>` query parameter (`401` otherwise).
