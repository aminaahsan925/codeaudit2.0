"""A&H Demo Shop, fixed variant.

A small shop app used to show the LaunchAudit fail loop. This variant
fixes the broken one: the key comes from the environment, the password
rule requires 8 or more characters with a digit, debug mode is off, and
checkout works end to end. Local demo only.
"""

import hashlib
import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

DEBUG = False

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shop.db"

app = FastAPI(title="A&H Demo Shop")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # The templates style themselves with one inline <style> block, so
    # style-src allows 'unsafe-inline'; scripts stay blocked (no inline
    # scripts anywhere) and everything else must come from this origin.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'"
    )
    return response


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

PRODUCTS = [
    ("Handmade Notebook", "Stitched paper notebook with a kraft cover.", 12.00),
    ("Ceramic Mug", "Glazed stoneware mug, 350 ml.", 18.00),
    ("Desk Lamp", "Warm light desk lamp with a wooden base.", 45.00),
    ("Canvas Tote", "Sturdy cotton tote for everyday carry.", 22.00),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, "
        "password_hash TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, "
        "price REAL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS orders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, "
        "total REAL, items TEXT)"
    )
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
            PRODUCTS,
        )
    conn.commit()
    conn.close()


init_db()


def hash_password(email, password):
    return hashlib.sha256(f"{email}:{password}".encode()).hexdigest()


def current_user(request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def read_cart(request):
    raw = request.cookies.get("cart", "")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def cart_items(request):
    ids = read_cart(request)
    if not ids:
        return [], 0.0
    conn = get_db()
    items = []
    total = 0.0
    for product_id in sorted(set(ids)):
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if row:
            qty = ids.count(product_id)
            items.append(
                {"product": row, "qty": qty, "subtotal": row["price"] * qty}
            )
            total += row["price"] * qty
    conn.close()
    return items, total


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"products": products, "user": current_user(request)},
    )


@app.post("/cart/add")
def add_to_cart(request: Request, product_id: int = Form(...)):
    ids = read_cart(request)
    ids.append(product_id)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("cart", ",".join(str(i) for i in ids), httponly=True, samesite="lax")
    return response


@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request):
    items, total = cart_items(request)
    return templates.TemplateResponse(
        request,
        "cart.html",
        {"items": items, "total": total, "user": current_user(request)},
    )


@app.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request):
    return templates.TemplateResponse(
        request, "signup.html", {"user": current_user(request)}
    )


@app.post("/signup", response_class=HTMLResponse)
def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    if len(password) < 8 or not any(ch.isdigit() for ch in password):
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "error": "Password must be at least 8 characters long and include a number.",
                "user": current_user(request),
            },
        )
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        conn.close()
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "error": "That email is already registered.",
                "user": current_user(request),
            },
        )
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, hash_password(email, password)),
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/login?note=signed_up", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, note: str = ""):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"note": note, "user": current_user(request)},
    )


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    if not row or row["password_hash"] != hash_password(email, password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Email or password is wrong.",
                "note": "",
                "user": current_user(request),
            },
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("user_id", str(row["id"]), httponly=True, samesite="lax")
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("user_id")
    return response


@app.get("/checkout", response_class=HTMLResponse)
def checkout(request: Request):
    items, total = cart_items(request)
    return templates.TemplateResponse(
        request,
        "checkout.html",
        {"items": items, "total": total, "user": current_user(request)},
    )


@app.post("/checkout/pay")
def pay(request: Request):
    items, total = cart_items(request)
    user = current_user(request)
    conn = get_db()
    conn.execute(
        "INSERT INTO orders (user_id, total, items) VALUES (?, ?, ?)",
        (
            user["id"] if user else None,
            total,
            json.dumps(
                [
                    {"name": item["product"]["name"], "qty": item["qty"]}
                    for item in items
                ]
            ),
        ),
    )
    order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    response = RedirectResponse(
        f"/order/done?order_id={order_id}", status_code=303
    )
    response.delete_cookie("cart")
    return response


@app.get("/order/done", response_class=HTMLResponse)
def order_done(request: Request, order_id: int = 0):
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return templates.TemplateResponse(
        request,
        "done.html",
        {"order": order, "user": current_user(request)},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8002"))
    uvicorn.run(app, host="127.0.0.1", port=port)
