"""Users, authentication helpers and the audit log."""
import re

from app.auth.security import hash_password, verify_password
from app.database.db import get_conn
from app.exceptions import ConflictError, NotFoundError, PermissionDenied, ValidationError

VALID_ROLES = ("recruiter", "admin")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def _public(row) -> dict:
    return {"id": row["id"], "username": row["username"], "role": row["role"],
            "created_at": row["created_at"]}


def log_action(actor: str, action: str, detail: str = "") -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO audit_log (actor, action, detail) VALUES (?, ?, ?)",
                     (actor, action, detail[:500]))


def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _public(row) if row else None


def authenticate(username: str, password: str) -> dict | None:
    """Return the public user dict if credentials are valid, else None."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return _public(row)
    return None


def create_user(username: str, password: str, role: str, actor: str = "system") -> dict:
    if not _USERNAME_RE.match(username or ""):
        raise ValidationError("Username must be 3-32 characters: letters, digits, _ . -")
    if len(password or "") < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if role not in VALID_ROLES:
        raise ValidationError(f"Role must be one of: {', '.join(VALID_ROLES)}.")
    if get_user_by_username(username):
        raise ConflictError("Username already exists.")
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                           (username, hash_password(password), role))
        user_id = cur.lastrowid
    log_action(actor, "create_user", f"{username} ({role})")
    return get_user_by_id(user_id)


def get_user_by_id(user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise NotFoundError("User not found.")
    return _public(row)


def list_users() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [_public(r) for r in rows]


def delete_user(user_id: int, acting_user: dict) -> None:
    target = get_user_by_id(user_id)
    if target["id"] == acting_user["id"]:
        raise PermissionDenied("You cannot delete your own account.")
    if target["role"] == "admin":
        admins = [u for u in list_users() if u["role"] == "admin"]
        if len(admins) <= 1:
            raise PermissionDenied("Cannot delete the last admin.")
    with get_conn() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    log_action(acting_user["username"], "delete_user", target["username"])


def list_audit(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
