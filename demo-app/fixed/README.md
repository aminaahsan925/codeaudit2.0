# A&H Demo Shop, fixed variant

Small shop app for the LaunchAudit demo, the "after" half of the fail to
fix loop. FastAPI, Jinja2 templates, SQLite file (`shop.db`, created on
first run). Built by Amina and Hadi, A&H Systems.

A LaunchAudit run against this variant reports risk 1.0, verdict
Launch, with the open CORS finding as the only remaining issue.

## Run

```bash
cd demo-app/fixed
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PORT=8002 .venv/bin/python app.py
```

Default port is 8002 if `PORT` is not set. Open http://127.0.0.1:8002.

## Routes

GET `/`, POST `/cart/add`, GET `/cart`, GET and POST `/signup`,
GET and POST `/login`, GET `/logout`, GET `/checkout`,
POST `/checkout/pay`, GET `/order/done`.

## What is fixed compared with the broken variant

1. The Stripe key is read from the environment instead of sitting in code.
2. Signup requires a password of 8 or more characters including a number.
3. Debug mode is switched off.
4. Checkout works: POST `/checkout/pay` creates the order and redirects
   to `/order/done`, which shows "Order placed" with the order id and total.
5. The app sends all four security headers: X-Content-Type-Options,
   X-Frame-Options, Referrer-Policy, and Content-Security-Policy.
6. Cookies are set with SameSite=lax.

One issue is left on purpose: the app still allows every origin through
CORS. That is the only remaining finding in the fixed run.
