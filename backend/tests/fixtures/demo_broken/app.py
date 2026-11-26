# fmt: off
# ruff: noqa
"""Replica of the broken demo app (test fixture, fake values only).

Carries the same code findings as the real broken demo: a planted test
secret, a weak password rule, and debug mode on. Parameterized queries
and hashlib.sha256 are the no-flag cases.
"""

import hashlib
import sqlite3

from fastapi import FastAPI, Form

# PLANTED DEMO SECRET (fake test key, not real)
STRIPE_SECRET_KEY = "sk_test_4a7b9c2d8e1f6a3b5c0d"  # gitleaks:allow

DEBUG = True

app = FastAPI(title="Demo Shop")


def hash_password(email, password):
    return hashlib.sha256(f"{email}:{password}".encode()).hexdigest()


@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...)):
    if len(password) < 4:
        return {"error": "Password must be at least 4 characters long."}
    conn = sqlite3.connect("shop.db")
    conn.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, hash_password(email, password)),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
