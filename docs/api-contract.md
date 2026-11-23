# API contract

Base URL (local): `http://localhost:8000`. All endpoints live under `/api`.
OpenAPI schema: `GET /api/openapi.json` (interactive docs at `/api/docs` outside production).
Frontend types are generated from the OpenAPI schema with `pnpm gen:api`; this
document describes intent, the OpenAPI schema is the machine-readable truth.

## Conventions

- JSON only, `snake_case` fields, timestamps in ISO 8601 UTC (`2026-11-23T18:00:00Z`).
- IDs are UUID v4 strings.
- Request bodies larger than `MAX_REQUEST_BYTES` (default 1 MB) are rejected with `413`.
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
| `engine` | enum | `semgrep`, `gitleaks`, `osv`, `vibe`, `live`, `journey`, `ai` |
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
