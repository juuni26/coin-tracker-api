import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import settings


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS coins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        symbol TEXT NOT NULL,
        market_cap_rank INTEGER,
        price_usd REAL NOT NULL,
        image_url TEXT,
        last_updated TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        coin_id INTEGER NOT NULL,
        added_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (coin_id) REFERENCES coins (id) ON DELETE CASCADE,
        UNIQUE (user_id, coin_id)
    )
    """,
)


def init_db(db_path: str | None = None) -> None:
    path = db_path or settings.DB_PATH
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        for stmt in SCHEMA_STATEMENTS:
            con.execute(stmt)
        con.commit()


@contextmanager
def get_connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or settings.DB_PATH
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()
