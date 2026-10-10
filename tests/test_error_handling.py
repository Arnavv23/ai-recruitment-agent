import pytest
import requests

from app.database import db
from app.exceptions import DatabaseError, LLMUnavailableError, VectorStoreError
from app.rag import vector_store
from app.services import llm_service


def test_llm_not_configured_raises():
    with pytest.raises(LLMUnavailableError):
        llm_service.call_llm("sys", "hi")


def test_llm_network_failure_and_bad_status(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-fake-key-for-testing-1234")

    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(LLMUnavailableError) as exc:
        llm_service.call_llm("s", "u")
    assert "sk-fake" not in exc.value.message  # key never leaks into errors

    class Resp:
        status_code = 500
    monkeypatch.setattr(requests, "post", lambda *a, **k: Resp())
    with pytest.raises(LLMUnavailableError):
        llm_service.call_llm("s", "u")
    text, used = llm_service.ask_llm_or_fallback("s", "u", "fallback")
    assert (text, used) == ("fallback", False)


def test_llm_malformed_response(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-fake-key-for-testing-1234")

    class Resp:
        status_code = 200
        def json(self):
            return {"unexpected": True}
    monkeypatch.setattr(requests, "post", lambda *a, **k: Resp())
    with pytest.raises(LLMUnavailableError):
        llm_service.call_llm("s", "u")


def test_database_failure_returns_clean_500(client, recruiter_headers, monkeypatch):
    def broken_conn():
        raise DatabaseError("Database is unavailable.")
    monkeypatch.setattr("app.services.job_service.get_conn", broken_conn)
    r = client.get("/jobs", headers=recruiter_headers)
    assert r.status_code == 500 and r.json()["detail"] == "Database is unavailable."


def test_vector_store_failure_rolls_back_candidate(client, recruiter_headers, python_pdf, monkeypatch):
    def broken(*a, **k):
        raise VectorStoreError("The vector database is unavailable.")
    monkeypatch.setattr(vector_store, "add_candidate_chunks", broken)
    r = client.post("/candidates/upload", files={"file": ("p.pdf", python_pdf, "application/pdf")},
                    headers=recruiter_headers)
    assert r.status_code == 500
    assert client.get("/candidates", headers=recruiter_headers).json() == []  # nothing half-saved


def test_oversized_upload_rejected(client, recruiter_headers, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    big = b"%PDF-1.4 " + b"0" * (1024 * 1024 + 10)
    r = client.post("/candidates/upload", files={"file": ("big.pdf", big, "application/pdf")},
                    headers=recruiter_headers)
    assert r.status_code == 400 and "too large" in r.json()["detail"]


def test_unexpected_error_does_not_leak_details(recruiter_headers, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app

    def crash(*a, **k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr("app.services.job_service.list_jobs", crash)
    r = TestClient(app, raise_server_exceptions=False).get("/jobs", headers=recruiter_headers)
    assert r.status_code == 500 and "secret" not in r.text
