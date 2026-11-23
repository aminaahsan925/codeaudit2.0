# A&H Demo Shop, broken variant

Small shop app for the LaunchAudit demo, the "before" half of the fail to
fix loop. FastAPI, Jinja2 templates, SQLite file (`shop.db`, created on
first run). Built by Amina and Hadi, A&H Systems.

A LaunchAudit run against this variant reports risk 8.3, verdict
Do not launch.

## Run

```bash
cd demo-app/broken
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PORT=8001 .venv/bin/python app.py
```

Default port is 8001 if `PORT` is not set. Open http://127.0.0.1:8001.

## Routes

GET `/`, POST `/cart/add`, GET `/cart`, GET and POST `/signup`,
GET and POST `/login`, GET `/logout`, GET `/checkout`,
POST `/checkout/pay`.

## What is wrong with this variant (intentional, for the demo)

1. A planted test-mode Stripe secret key sits in `app.py` as a plain
   assignment. It is a fake demo key, not a real credential.
2. The signup password rule accepts very short passwords.
3. Debug mode is switched on.
4. Checkout always fails: POST `/checkout/pay` returns HTTP 500 with a
   "Payment failed" page. There is no order confirmation page.
5. The app sends no security headers.
6. Cookies are set without SameSite.

The fixed variant lives in `../fixed/` and corrects all six.
