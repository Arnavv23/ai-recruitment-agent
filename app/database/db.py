"""SQLite connection helper, schema creation and first-admin seeding."""
import logging
import secrets
import sqlite3
from contextlib import contextmanager

from app.config import settings
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('recruiter', 'admin')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    required_skills TEXT NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    skills TEXT NOT NULL DEFAULT '[]',
    experience_years REAL DEFAULT 0,
    resume_text TEXT NOT NULL,
    file_name TEXT,
    uploaded_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def get_conn():
    """Open a connection, commit on success, roll back on error."""
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(settings.db_path, timeout=10)
    except (sqlite3.Error, OSError) as exc:
        logger.error("Cannot open database: %s", exc)
        raise DatabaseError("Database is unavailable.") from exc
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        logger.error("Database error: %s", exc)
        raise DatabaseError("A database error occurred.") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and make sure at least one admin exists."""
    from app.auth.security import hash_password  # local import avoids cycles

    with get_conn() as conn:
        conn.executescript(SCHEMA)
        has_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
        if not has_users:
            password = settings.admin_password
            generated = False
            if not password:
                password = secrets.token_urlsafe(12)
                generated = True
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                (settings.admin_username, hash_password(password)),
            )
            if generated:
                # Shown once, on the server console only.
                print(f"\n[SETUP] Admin '{settings.admin_username}' created. "
                      f"Temporary password: {password}\n")
            else:
                logger.info("Admin user '%s' created from environment.", settings.admin_username)
