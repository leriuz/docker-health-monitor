"""SQLite storage for health check results."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Generator, Optional

DB_PATH = os.environ.get("DB_PATH", "/data/checks.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent read/write
    return conn


@contextmanager
def db_session(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Create tables if they don't exist."""
    with db_session(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS check_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_name TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms REAL,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_endpoint_time
            ON check_results (endpoint_name, checked_at DESC)
        """)


def insert_result(
    endpoint_name: str,
    url: str,
    status: str,
    status_code: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    error_message: Optional[str] = None,
    db_path: str = DB_PATH,
) -> None:
    """Record a health check result."""
    with db_session(db_path) as conn:
        conn.execute(
            """INSERT INTO check_results
               (endpoint_name, url, status, status_code, response_time_ms, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (endpoint_name, url, status, status_code, response_time_ms, error_message),
        )


def get_latest_results(db_path: str = DB_PATH) -> list[dict]:
    """Get the most recent check result for each endpoint."""
    with db_session(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM check_results
            WHERE id IN (
                SELECT MAX(id) FROM check_results GROUP BY endpoint_name
            )
            ORDER BY endpoint_name
        """).fetchall()
        return [dict(row) for row in rows]


def get_history(
    endpoint_name: str, limit: int = 50, db_path: str = DB_PATH
) -> list[dict]:
    """Get recent check history for an endpoint."""
    with db_session(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM check_results
               WHERE endpoint_name = ?
               ORDER BY checked_at DESC LIMIT ?""",
            (endpoint_name, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_uptime_percent(
    endpoint_name: str, hours: int = 24, db_path: str = DB_PATH
) -> float:
    """Calculate uptime percentage over a time window."""
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with db_session(db_path) as conn:
        row = conn.execute(
            """SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) as up_count
               FROM check_results
               WHERE endpoint_name = ? AND checked_at >= ?""",
            (endpoint_name, cutoff),
        ).fetchone()
        total = row["total"]
        if total == 0:
            return 0.0
        return round((row["up_count"] / total) * 100, 2)


def get_consecutive_failures(
    endpoint_name: str, db_path: str = DB_PATH
) -> int:
    """Count consecutive failures from the most recent check backwards."""
    with db_session(db_path) as conn:
        rows = conn.execute(
            """SELECT status FROM check_results
               WHERE endpoint_name = ?
               ORDER BY checked_at DESC LIMIT 20""",
            (endpoint_name,),
        ).fetchall()

    count = 0
    for row in rows:
        if row["status"] != "UP":
            count += 1
        else:
            break
    return count
