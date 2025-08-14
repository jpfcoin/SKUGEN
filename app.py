import os
from flask import Flask, jsonify, render_template
import psycopg2

# ====== SKU alphabet & helpers ======
SAFE_CHARS = '0123456789ACDEFGHJKLMNPRTUVWXYZ'  # 32-char alphabet (no B, I, O, S)
BASE = len(SAFE_CHARS)
MAX_COUNT = BASE ** 4  # 32^4 = 1,048,576

def int_to_sku(n: int) -> str:
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
    url = os.environ["DATABASE_URL"]  # set this in Render → Environment
    return psycopg.connect(url)

def ensure_pg_objects():
    """
    Create the global counter sequence starting just past '9999' -> '999A' (decimal 304426),
    and an optional audit table to record issued counters.
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

# Run once on import (best-effort)
try:
    ensure_pg_objects()
except Exception:
    # If the DB isn't reachable at import time, the first request will still work;
    # we don't crash the app here.
    pass

def get_next_counter() -> int:
    """
    Atomically obtain the next global counter from PostgreSQL.
    nextval() is concurrency-safe across multiple workers/instances.
    """
    with get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('sku_counter')")
            (n,) = cur.fetchone()
            # Optional audit insert (ignore if table missing or duplicate)
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
        # Return message for quick diagnosis; adjust if you prefer a generic error
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return "ok"

if __name__ == "__main__":
    # Local dev: run Flask's server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
