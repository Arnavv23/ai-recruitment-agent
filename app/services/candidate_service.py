"""Candidates: upload, store, list, search (RAG) and delete."""
import json
import logging
from collections import Counter

from app.config import settings
from app.database.db import get_conn
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.rag import vector_store
from app.rag.chunking import chunk_text
from app.services.pdf_service import extract_text_from_pdf
from app.services.resume_parser import parse_resume
from app.services.user_service import log_action

logger = logging.getLogger(__name__)


def _row(row, include_text: bool = False) -> dict:
    d = dict(row)
    d["skills"] = json.loads(d.get("skills") or "[]")
    if not include_text:
        d.pop("resume_text", None)
    return d


def create_candidate_from_pdf(file_name: str, data: bytes, uploaded_by: str) -> dict:
    """PDF -> text -> parsed fields -> SQLite -> chunks -> embeddings -> ChromaDB."""
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValidationError(f"File is too large (max {settings.max_upload_mb} MB).")
    text = extract_text_from_pdf(data)
    info = parse_resume(text, file_name)

    if info["email"]:
        with get_conn() as conn:
            dup = conn.execute("SELECT id FROM candidates WHERE email = ?", (info["email"],)).fetchone()
        if dup:
            raise ConflictError(f"A candidate with email {info['email']} already exists (id {dup['id']}).")

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO candidates (name, email, phone, skills, experience_years, resume_text, file_name, uploaded_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (info["name"], info["email"], info["phone"], json.dumps(info["skills"]),
             info["experience_years"], text, file_name, uploaded_by))
        candidate_id = cur.lastrowid
    try:
        vector_store.add_candidate_chunks(candidate_id, info["name"], chunk_text(text))
    except Exception:
        # keep SQLite and ChromaDB consistent: undo the insert if indexing failed
        with get_conn() as conn:
            conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        raise
    log_action(uploaded_by, "upload_resume", f"{info['name']} (id {candidate_id})")
    return get_candidate(candidate_id)


def get_candidate(candidate_id: int, include_text: bool = False) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not row:
        raise NotFoundError(f"Candidate {candidate_id} not found.")
    return _row(row, include_text)


def list_candidates(skill: str | None = None) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM candidates ORDER BY id DESC").fetchall()
    candidates = [_row(r) for r in rows]
    if skill:
        skill = skill.strip().lower()
        candidates = [c for c in candidates if skill in c["skills"]]
    return candidates


def delete_candidate(candidate_id: int, actor: str) -> None:
    cand = get_candidate(candidate_id)
    vector_store.delete_candidate_chunks(candidate_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
    log_action(actor, "delete_candidate", f"{cand['name']} (id {candidate_id})")


def search_candidates(query: str, top_k: int = 5) -> list[dict]:
    """Natural-language search: query embedding -> nearest resume chunks -> grouped by candidate."""
    query = (query or "").strip()
    if len(query) < 2:
        raise ValidationError("Search query is too short.")
    hits = vector_store.search_chunks(query, top_k=top_k * 4)
    grouped: dict[int, dict] = {}
    for hit in hits:  # hits are already best-first
        entry = grouped.setdefault(hit["candidate_id"], {"score": hit["score"], "snippets": []})
        if len(entry["snippets"]) < 2:
            entry["snippets"].append(hit["text"])
    results = []
    for cid, entry in grouped.items():
        try:
            cand = get_candidate(cid)
        except NotFoundError:
            logger.warning("Vector entry for missing candidate %s ignored.", cid)
            continue
        results.append({"candidate_id": cid, "name": cand["name"], "skills": cand["skills"],
                        "experience_years": cand["experience_years"],
                        "score": round(entry["score"], 3), "snippets": entry["snippets"]})
        if len(results) >= top_k:
            break
    return results


def dashboard_stats() -> dict:
    with get_conn() as conn:
        n_cand = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        n_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    skills = Counter(s for c in list_candidates() for s in c["skills"])
    return {"candidates": n_cand, "jobs": n_jobs, "top_skills": dict(skills.most_common(10))}
