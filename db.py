import sqlite3
from datetime import datetime, timezone

DB_PATH = "cloudops.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the tables if they don't exist yet."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                status_code INTEGER,
                response_time REAL,
                error TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checks_url_time ON checks (url, checked_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                started_at TEXT NOT NULL,
                resolved_at TEXT,
                reason TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_check(result: dict, db_path: str = DB_PATH) -> None:
    """Insert one check result."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO checks (checked_at, url, status, status_code, response_time, error) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                result["url"],
                result["status"],
                result["status_code"],
                result["response_time"],
                result["error"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_checks(limit: int = 10, db_path: str = DB_PATH) -> list:
    conn = get_connection(db_path)
    try:
        return conn.execute(
            "SELECT * FROM checks ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()

def get_open_incident(url: str, db_path: str = DB_PATH):
    """Return the unresolved incident for this URL, or None."""
    conn = get_connection(db_path)
    try:
        return conn.execute(
            "SELECT * FROM incidents WHERE url = ? AND resolved_at IS NULL", (url,)
        ).fetchone()
    finally:
        conn.close()


def open_incident(url: str, reason: str, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO incidents (url, started_at, reason) VALUES (?, ?, ?)",
            (url, datetime.now(timezone.utc).isoformat(timespec="seconds"), reason),
        )
        conn.commit()
    finally:
        conn.close()


def resolve_incident(incident_id: int, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE incidents SET resolved_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), incident_id),
        )
        conn.commit()
    finally:
        conn.close()


def count_consecutive_failures(url: str, limit: int, db_path: str = DB_PATH) -> int:
    """Count how many of the most recent checks for this URL failed in a row."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT status FROM checks WHERE url = ? ORDER BY id DESC LIMIT ?",
            (url, limit),
        ).fetchall()
    finally:
        conn.close()
    count = 0
    for row in rows:
        if row["status"] == "DOWN":
            count += 1
        else:
            break
    return count
