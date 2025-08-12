import os
import sqlite3
from flask import Flask, jsonify, render_template, request, send_from_directory, abort
from contextlib import closing

SAFE_CHARS = '0123456789ACDEFGHJKLMNPRTUVWXYZ'  # 32-char alphabet (no B, I, O, S)
BASE = len(SAFE_CHARS)
MAX_COUNT = BASE ** 4  # 32^4 = 1,048,576

DB_PATH = os.environ.get("DATABASE_PATH", "sku.db")

app = Flask(__name__)

# Initialize DB on import for hosted environments
init_db_called = False

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE IF NOT EXISTS counter (id INTEGER PRIMARY KEY CHECK (id=1), value INTEGER NOT NULL)")
        # Initialize single-row counter if missing
        cur = conn.execute("SELECT value FROM counter WHERE id=1")
        row = cur.fetchone()
        if row is None:
            conn.execute("INSERT INTO counter (id, value) VALUES (1, 0)")
        conn.commit()

def int_to_sku(n: int) -> str:
    if n < 0 or n >= MAX_COUNT:
        raise ValueError("Counter out of range for 4-character space.")
    out = []
    for _ in range(4):
        out.append(SAFE_CHARS[n % BASE])
        n //= BASE
    return ''.join(reversed(out))

def get_next_counter() -> int:
    """Atomically get and increment the counter, returning the previous value."""
    with closing(sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute("SELECT value FROM counter WHERE id=1")
        row = cur.fetchone()
        if row is None:
            conn.execute("INSERT INTO counter (id, value) VALUES (1, 0)")
            current = 0
        else:
            current = row[0]
        if current >= MAX_COUNT:
            conn.execute("COMMIT")
            raise ValueError("SKU space exhausted (over 1,048,576 issued).")
        conn.execute("UPDATE counter SET value = value + 1 WHERE id=1")
        conn.execute("COMMIT")
        return current

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/next", methods=["POST"])
def api_next():
    try:
        n = get_next_counter()
        sku = int_to_sku(n)
        return jsonify({"sku": sku})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/healthz")
def healthz():
    return "ok"

if not init_db_called:
    init_db()
    init_db_called = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
