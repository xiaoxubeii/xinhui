from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings


def init_db(db_path: Path | None = None) -> None:
    """Initialize SQLite tables for annotations and consensus."""
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id TEXT NOT NULL,
            reader_id TEXT NOT NULL,
            role TEXT NOT NULL,
            at_time REAL NOT NULL,
            smoothing TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS consensus (
            exam_id TEXT PRIMARY KEY,
            delta REAL NOT NULL,
            status TEXT NOT NULL,
            t_a REAL,
            t_b REAL,
            t_c REAL,
            t_gt REAL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


@contextmanager
def db_conn(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
