import sqlite3
from datetime import datetime, timezone

DB_PATH = "cloudops.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the table if it doesn't exist yet."""
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
