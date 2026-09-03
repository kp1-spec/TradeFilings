"""SQLite storage for filings seen and transactions parsed."""
import os
import json
import sqlite3

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "trades.db")
JSON_PATH = os.path.join(DATA_DIR, "trades.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS filings (
  doc_id TEXT PRIMARY KEY,
  source TEXT DEFAULT 'House',
  filer TEXT,
  doc_url TEXT,
  status TEXT,
  seen_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT, filer TEXT, state_district TEXT,
  owner TEXT, asset TEXT, ticker TEXT, asset_type TEXT,
  tx_type TEXT, tx_date TEXT, notified_date TEXT,
  amount_low INTEGER, amount_high INTEGER,
  filing_date TEXT, doc_id TEXT, doc_url TEXT, collected_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_tx_doc ON transactions(doc_id);
CREATE INDEX IF NOT EXISTS ix_tx_amount ON transactions(amount_low);
"""

COLS = ["source", "filer", "state_district", "owner", "asset", "ticker", "asset_type",
        "tx_type", "tx_date", "notified_date", "amount_low", "amount_high",
        "filing_date", "doc_id", "doc_url", "collected_at"]


def conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.executescript(SCHEMA)
    return c


def seen(doc_id):
    with conn() as c:
        return c.execute("SELECT 1 FROM filings WHERE doc_id=?", (doc_id,)).fetchone() is not None


def mark_seen(doc_id, status, filer=None, doc_url=None, source="House"):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO filings(doc_id, source, filer, doc_url, status) VALUES (?,?,?,?,?)",
                  (doc_id, source, filer, doc_url, status))


def add_transactions(rows):
    if not rows:
        return
    with conn() as c:
        c.executemany(
            f"INSERT INTO transactions({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))})",
            [tuple(r.get(k) for k in COLS) for r in rows],
        )


def all_transactions(limit=5000):
    with conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            f"SELECT {','.join(COLS)} FROM transactions ORDER BY filing_date DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def export_json():
    """Write data/trades.json for the dashboard and for your own use."""
    rows = all_transactions()
    with open(JSON_PATH, "w") as f:
        json.dump(rows, f, indent=0)
    return rows
