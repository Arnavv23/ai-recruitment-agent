import pytest

from app.exceptions import ResumeProcessingError
from app.rag.chunking import chunk_text
from app.services.pdf_service import extract_text_from_pdf
from app.services.resume_parser import extract_skills, parse_resume
from tests.helpers import PYTHON_RESUME, make_pdf


def test_extract_text_from_valid_pdf(python_pdf):
    text = extract_text_from_pdf(python_pdf)
    assert "Priya Sharma" in text and "Django" in text


@pytest.mark.parametrize("data", [b"", b"this is not a pdf", b"%PDF-1.4 broken garbage"])
def test_invalid_pdf_raises(data):
    with pytest.raises(ResumeProcessingError):
        extract_text_from_pdf(data)


def test_pdf_without_text_raises():
    with pytest.raises(ResumeProcessingError):
        extract_text_from_pdf(make_pdf([""]))


def test_parse_resume_fields(python_pdf):
    info = parse_resume(extract_text_from_pdf(python_pdf), "priya.pdf")
    assert info["name"] == "Priya Sharma"
    assert info["email"] == "priya.sharma@example.com"
    assert info["experience_years"] == 4.0
    assert {"python", "django", "docker"} <= set(info["skills"])


def test_skill_matching_is_whole_word():
    assert "java" not in extract_skills("I love javascript")
    assert "c++" in extract_skills("Experienced in C++ and Go")


def test_chunking_overlap_and_limits():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 3 and all(len(c) <= 200 for c in chunks)
    assert chunk_text("") == [] and chunk_text("short text") == ["short text"]


def test_upload_invalid_files_via_api(client, recruiter_headers):
    r = client.post("/candidates/upload", files={"file": ("cv.pdf", b"not a pdf", "application/pdf")},
                    headers=recruiter_headers)
    assert r.status_code == 400
    r = client.post("/candidates/upload", files={"file": ("cv.txt", b"hello", "text/plain")},
                    headers=recruiter_headers)
    assert r.status_code == 400
    r = client.post("/candidates/upload", files={"file": ("empty.pdf", make_pdf([""]), "application/pdf")},
                    headers=recruiter_headers)
    assert r.status_code == 400 and "No readable text" in r.json()["detail"]


def test_duplicate_email_rejected(client, recruiter_headers, python_pdf):
    files = {"file": ("priya.pdf", python_pdf, "application/pdf")}
    assert client.post("/candidates/upload", files=files, headers=recruiter_headers).status_code == 201
    assert client.post("/candidates/upload", files=files, headers=recruiter_headers).status_code == 409


def test_unreadable_lines_helper_constants():
    assert PYTHON_RESUME[0] == "Priya Sharma"
