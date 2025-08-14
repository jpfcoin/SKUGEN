import os
from flask import Flask, jsonify, render_template
import psycopg  # psycopg v3 (works on Python 3.13)

# ====== SKU alphabet & helpers ======
SAFE_CHARS = '0123456789ACDEFGHJKLMNPRTUVWXYZ'  # 32-char alphabet (no B, I, O, S)
BASE = len(SAFE_CHARS)
MAX_COUNT = BASE ** 4  # 32^4 = 1,048,576

def int_to_sku(n: int) -> str:
    """Convert a non-negative int to a 4-char SKU using SAFE_CHARS."""
    if n < 0 or n >= MAX_COUNT:
        raise ValueError("Counter out of range for 4-character space.")
    out = []
    for _ in range(4):
        out.append(SAFE_CHARS[n % BASE])
        n //= BASE
    return ''.join(reversed(out))

# ====== Flask app ======
app = Flask(__name__)

# ====== PostgreSQL utilities ======
def get_pg_conn():
    """Open a connection using DATABASE_URL (set in Render → Environment)."""
    url = os.environ["DATABASE_URL"]  # e.g., postgres://...
    # psycopg v3 supports connection strings directly
    return psycopg.connect(url)

def ensure_pg_objects():
    """
    Ensure the global counter sequence and optional audit table exist.
    Sequence starts just past '9999' → '999A' (decimal 304426).
    Safe to run more than once.
    """
    ddl = """
    CREATE SEQUENCE IF NOT EXISTS sku_counter START WITH 304426;

    CREATE TABLE IF NOT EXISTS issued_skus (
      n BIGINT PRIMARY KEY,
      created_at TIMESTAMPTZ DEFAULT now()
    );
    """
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()

# Best-effort init on import (if DB temporarily unreachable, requests will still try later)
try:
    ensure_pg_objects()
except Exception:
    pass

def get_next_counter() -> int:
    """
    Atomically obtain the next global counter from PostgreSQL.
    nextval() is concurrency-safe across workers/instances.
    """
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('sku_counter')")
            (n,) = cur.fetchone()
            # Optional audit insert; ignore any errors to keep issuance fast
            try:
                cur.execute("INSERT INTO issued_skus (n) VALUES (%s)", (n,))
            except Exception:
                pass
        conn.commit()
    return n

# ====== Routes ======
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/next", methods=["POST"])
def api_next():
    try:
        n = get_next_counter()
        sku = int_to_sku(n)
        return jsonify({"sku": sku})
    except Exception as e:
        # Surface the error for easier troubleshooting; change to a generic message if preferred
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return "ok"

if __name__ == "__main__":
    # Local dev: run Flask's built-in server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
