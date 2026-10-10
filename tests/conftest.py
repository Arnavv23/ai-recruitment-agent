import pytest
from fastapi.testclient import TestClient

from app.database.db import init_db
from app.services import user_service
from main import app
from tests.helpers import JOB_TEXT, PYTHON_RESUME, SECURITY_RESUME, make_pdf


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Every test gets its own database + vector store and no real LLM."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only-0123456789")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123!")
    monkeypatch.setenv("LLM_API_KEY", "")
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def _login(client, username, password):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    return _login(client, "admin", "AdminPass123!")


@pytest.fixture
def recruiter_headers(client):
    user_service.create_user("recruiter1", "RecruiterPass1!", "recruiter")
    return _login(client, "recruiter1", "RecruiterPass1!")


@pytest.fixture
def python_pdf():
    return make_pdf(PYTHON_RESUME)


@pytest.fixture
def security_pdf():
    return make_pdf(SECURITY_RESUME)


@pytest.fixture
def uploaded(client, recruiter_headers, python_pdf, security_pdf):
    """Two uploaded candidates and one job. Returns their IDs."""
    ids = []
    for name, pdf in (("priya.pdf", python_pdf), ("rahul.pdf", security_pdf)):
        r = client.post("/candidates/upload", files={"file": (name, pdf, "application/pdf")},
                        headers=recruiter_headers)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    job = client.post("/jobs", json={"title": "Backend Developer", "description": JOB_TEXT},
                      headers=recruiter_headers)
    assert job.status_code == 201, job.text
    return {"candidates": ids, "job": job.json()["id"], "headers": recruiter_headers}
