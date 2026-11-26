# fmt: off
# ruff: noqa
"""Replica of the fixed demo app (test fixture).

The key comes from the environment, the password rule is strong, debug
is off, and checkout works. The only code finding is the CORS wildcard.
"""

import hashlib
import os
import sqlite3

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

DEBUG = False

app = FastAPI(title="Demo Shop")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)


def hash_password(email, password):
    return hashlib.sha256(f"{email}:{password}".encode()).hexdigest()


@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...)):
    if len(password) < 8 or not any(ch.isdigit() for ch in password):
        return {"error": "Password must be at least 8 characters long."}
    conn = sqlite3.connect("shop.db")
    conn.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, hash_password(email, password)),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
