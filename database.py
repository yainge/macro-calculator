"""
database.py — SQLite setup and all query functions.

Uses Flask's `g` object for per-request connections.
"""

import sqlite3
import datetime
from flask import g

DATABASE = "macro_calculator.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables and register teardown. Called once at app startup."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id          INTEGER PRIMARY KEY CHECK (id = 1),
                protein_g   REAL NOT NULL DEFAULT 0,
                fat_g       REAL NOT NULL DEFAULT 0,
                carbs_g     REAL NOT NULL DEFAULT 0,
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS log_entries (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_date  TEXT NOT NULL,
                description  TEXT NOT NULL,
                protein_g    REAL NOT NULL DEFAULT 0,
                fat_g        REAL NOT NULL DEFAULT 0,
                carbs_g      REAL NOT NULL DEFAULT 0,
                calories     REAL,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_log_date ON log_entries(logged_date);
        """)
        db.commit()


# ── Goals ──────────────────────────────────────────────────────

def get_goals():
    row = get_db().execute("SELECT protein_g, fat_g, carbs_g FROM goals WHERE id = 1").fetchone()
    if row:
        return {"protein_g": row["protein_g"], "fat_g": row["fat_g"], "carbs_g": row["carbs_g"]}
    return {"protein_g": 0, "fat_g": 0, "carbs_g": 0}


def upsert_goals(protein_g, fat_g, carbs_g):
    db = get_db()
    db.execute(
        """
        INSERT INTO goals (id, protein_g, fat_g, carbs_g, updated_at)
        VALUES (1, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            protein_g  = excluded.protein_g,
            fat_g      = excluded.fat_g,
            carbs_g    = excluded.carbs_g,
            updated_at = excluded.updated_at
        """,
        (protein_g, fat_g, carbs_g),
    )
    db.commit()


# ── Log entries ────────────────────────────────────────────────

def _today():
    return datetime.date.today().isoformat()


def get_log():
    rows = get_db().execute(
        "SELECT id, description, protein_g, fat_g, carbs_g, calories, created_at "
        "FROM log_entries WHERE logged_date = ? ORDER BY created_at",
        (_today(),),
    ).fetchall()

    entries = [dict(r) for r in rows]
    totals = {
        "protein_g": round(sum(e["protein_g"] for e in entries), 1),
        "fat_g":     round(sum(e["fat_g"]     for e in entries), 1),
        "carbs_g":   round(sum(e["carbs_g"]   for e in entries), 1),
        "calories":  round(sum(e["calories"] or 0 for e in entries), 1),
    }
    return entries, totals


def insert_log_entry(description, protein_g, fat_g, carbs_g, calories):
    db = get_db()
    cur = db.execute(
        "INSERT INTO log_entries (logged_date, description, protein_g, fat_g, carbs_g, calories) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_today(), description, protein_g, fat_g, carbs_g, calories),
    )
    db.commit()
    return cur.lastrowid


def delete_log_entry(entry_id):
    """Delete an entry only if it belongs to today. Returns True if deleted."""
    db = get_db()
    cur = db.execute(
        "DELETE FROM log_entries WHERE id = ? AND logged_date = ?",
        (entry_id, _today()),
    )
    db.commit()
    return cur.rowcount > 0
