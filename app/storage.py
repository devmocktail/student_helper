"""SQLite persistence for answer history and flashcards.

Lives in ~/.studyhelper/studyhelper.db so it survives code updates and never
touches the repo.
"""

import sqlite3
import time

from app import config


def _conn():
    config.ensure_app_dir()
    conn = sqlite3.connect(config.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created REAL, mode TEXT, title TEXT, answer TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS cards(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created REAL, front TEXT, back TEXT,
                interval REAL, reps INTEGER, ef REAL, due REAL, lapses INTEGER)"""
        )


# --- history ---------------------------------------------------------------
def add_history(mode, title, answer):
    with _conn() as c:
        c.execute(
            "INSERT INTO history(created, mode, title, answer) VALUES(?,?,?,?)",
            (time.time(), mode, title, answer),
        )


def list_history(limit=200):
    with _conn() as c:
        return c.execute(
            "SELECT * FROM history ORDER BY created DESC LIMIT ?", (limit,)
        ).fetchall()


# --- flashcards ------------------------------------------------------------
def add_card(front, back):
    now = time.time()
    with _conn() as c:
        c.execute(
            """INSERT INTO cards(created, front, back, interval, reps, ef, due, lapses)
               VALUES(?,?,?,?,?,?,?,?)""",
            (now, front, back, 0, 0, 2.5, now, 0),
        )


def due_cards():
    now = time.time()
    with _conn() as c:
        return c.execute(
            "SELECT * FROM cards WHERE due <= ? ORDER BY due ASC", (now,)
        ).fetchall()


def all_cards():
    with _conn() as c:
        return c.execute("SELECT * FROM cards ORDER BY created DESC").fetchall()


def update_card(card_id, interval, reps, ef, due, lapses):
    with _conn() as c:
        c.execute(
            """UPDATE cards SET interval=?, reps=?, ef=?, due=?, lapses=? WHERE id=?""",
            (interval, reps, ef, due, lapses, card_id),
        )


def delete_card(card_id):
    with _conn() as c:
        c.execute("DELETE FROM cards WHERE id=?", (card_id,))


def stats():
    with _conn() as c:
        total_cards = c.execute("SELECT COUNT(*) n FROM cards").fetchone()["n"]
        total_hist = c.execute("SELECT COUNT(*) n FROM history").fetchone()["n"]
        now = time.time()
        due = c.execute(
            "SELECT COUNT(*) n FROM cards WHERE due <= ?", (now,)
        ).fetchone()["n"]
    return {"cards": total_cards, "history": total_hist, "due": due}
