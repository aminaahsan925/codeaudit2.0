# LaunchAudit demo shop

Two variants of the same small shop app, used to show the LaunchAudit
fail to fix loop. Each variant is a FastAPI app with Jinja2 templates
and a SQLite file (`shop.db`, created on first run). Built by Amina and
Hadi, A&H Systems.

## Variants

- `broken/` (port 8001): the "before" app. A LaunchAudit run reports
  risk 8.3, verdict Do not launch. It carries a planted test-mode Stripe
  secret key as a plain assignment in `app.py`, a weak signup password
  rule, debug mode on, a checkout that always fails with HTTP 500, no
  security headers, and cookies without SameSite.
- `fixed/` (port 8002): the "after" app. A LaunchAudit run reports
  risk 1.0, verdict Launch. The key comes from the environment, signup
  requires 8 or more characters with a number, debug mode is off,
  checkout works end to end, all four security headers are sent, and
  cookies carry SameSite=lax. The one intentional remaining issue is
  CORS open to any origin.

The planted key in the broken variant is a fake demo key, not a real
credential. It is allowlisted in the repo `.gitleaks.toml` so secret
scanning still passes.

## Run

Each variant gets its own pip venv. From the repo root:

```bash
cd demo-app/broken
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PORT=8001 .venv/bin/python app.py
```

```bash
cd demo-app/fixed
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PORT=8002 .venv/bin/python app.py
```

Broken runs on http://127.0.0.1:8001, fixed on
http://127.0.0.1:8002. See each variant README for its routes and the
full list of intentional issues.

## Notes

- Local demo only. Do not deploy either variant.
- `shop.db` files are runtime data and are gitignored; never commit them.
