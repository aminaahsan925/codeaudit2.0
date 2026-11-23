## What changed

<!-- Summary of the change and why. Link the feature in docs/features.md. -->

## How to test

<!-- Exact steps a reviewer can follow: commands, URLs, expected results. -->

1.

## Checklist

- [ ] Branch is `feat/<slug>` (or `fix/`, `chore/`) from the latest `main`
- [ ] Tests added or updated for this change
- [ ] Backend: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` pass
- [ ] Frontend: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` pass
- [ ] OpenAPI schema exported and `pnpm gen:api` run if the API changed
- [ ] No secrets, `.env` files or real credentials committed
- [ ] Security rules in CONTRIBUTING.md followed (env access, SQL, input validation, no shell/eval)
- [ ] UI has loading, empty and error states (if UI changed)
- [ ] `docs/` updated (features status, API contract, decisions)

## Screenshots

<!-- Desktop and mobile, light and dark, for any UI change. Delete if none. -->
