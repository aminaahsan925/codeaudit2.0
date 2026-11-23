@CONTRIBUTING.md

# Assistant rules

Everything in CONTRIBUTING.md applies. These rules are extra, for coding
assistants working in this repo.

## Plan first
Before writing code, state the branch name, the files you will touch, the
subagents you will use and the tests you will add. Wait for approval on
anything larger than a small fix.

## Use the subagents
The team lives in `.claude/agents/`:
- `backend-dev`: everything under `backend/` (strict layers from CONTRIBUTING.md).
- `frontend-dev`: everything under `frontend/`; always loads the `frontend-design` skill first.
- `test-writer`: pytest, Vitest + RTL and Playwright for every feature.
- `ui-reviewer`: runs the app, checks it in Chrome at desktop and mobile width, reports issues with screenshots.
- `security-reviewer`: read-only review of the diff before finishing. Never edits.

Run backend-dev and frontend-dev in parallel when a feature touches both,
test-writer alongside, and both reviewers before calling a feature done.

## No attribution
- No `Co-Authored-By` or other trailers in commit messages.
- No "Generated with ..." or similar lines in commit messages, PR titles, PR
  bodies or PR comments.
- Commits are authored only by the developer's own git identity.
- `.claude/settings.json` turns attribution off; do not override it in
  `.claude/settings.local.json`.

## Key decisions
Every project decision (stack, layering, branch naming, commit style, AI
providers, attribution) is recorded in [docs/decisions.md](docs/decisions.md).
Read it before proposing an alternative, and add an entry when you make a new
decision.
