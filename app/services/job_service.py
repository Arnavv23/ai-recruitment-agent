"""Job descriptions."""
import json

from app.database.db import get_conn
from app.exceptions import NotFoundError, ValidationError
from app.services.pdf_service import extract_text_from_pdf
from app.services.resume_parser import extract_skills
from app.services.user_service import log_action


def _row(row) -> dict:
    d = dict(row)
    d["required_skills"] = json.loads(d.get("required_skills") or "[]")
    return d


def create_job(title: str, description: str, created_by: str, required_skills: list[str] | None = None) -> dict:
    title, description = (title or "").strip(), (description or "").strip()
    if len(title) < 3:
        raise ValidationError("Job title must be at least 3 characters.")
    if len(description) < 20:
        raise ValidationError("Job description must be at least 20 characters.")
    skills = [s.strip().lower() for s in (required_skills or []) if s.strip()] or extract_skills(description)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (title, description, required_skills, created_by) VALUES (?, ?, ?, ?)",
            (title, description, json.dumps(skills), created_by))
        job_id = cur.lastrowid
    log_action(created_by, "create_job", f"{title} (id {job_id})")
    return get_job(job_id)


def create_job_from_file(title: str, filename: str, data: bytes, created_by: str) -> dict:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        text = extract_text_from_pdf(data)
    elif name.endswith(".txt"):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("Text file must be UTF-8 encoded.") from exc
    else:
        raise ValidationError("Only .pdf or .txt job descriptions are supported.")
    return create_job(title, text, created_by)


def get_job(job_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise NotFoundError(f"Job {job_id} not found.")
    return _row(row)


def list_jobs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return [_row(r) for r in rows]


def delete_job(job_id: int, actor: str) -> None:
    job = get_job(job_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    log_action(actor, "delete_job", f"{job['title']} (id {job_id})")
