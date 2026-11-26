"""A&H Demo Shop, broken variant.

A small shop app used to show the LaunchAudit fail loop. This variant
carries a planted test secret, a weak password rule, debug mode on, and
a checkout that fails at payment. Local demo only.
"""

import hashlib
import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# PLANTED DEMO SECRET (test key, not real)
STRIPE_SECRET_KEY = "sk_test_9f2k7x4q8w1z3m5n7b0c"

DEBUG = True

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shop.db"

app = FastAPI(title="A&H Demo Shop")
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
    response.set_cookie("cart", ",".join(str(i) for i in ids), httponly=True, samesite=None)
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
    if len(password) < 4:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "error": "Password must be at least 4 characters long.",
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
    response.set_cookie("user_id", str(row["id"]), httponly=True, samesite=None)
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


@app.post("/checkout/pay", response_class=HTMLResponse)
def pay(request: Request):
    # Broken checkout: the payment step always fails in this variant.
    return templates.TemplateResponse(
        request,
        "payment_failed.html",
        {"user": current_user(request)},
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)
