from tests.helpers import JOB_TEXT, make_pdf


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_job_crud_and_validation(client, recruiter_headers, admin_headers):
    r = client.post("/jobs", json={"title": "Backend Developer", "description": JOB_TEXT}, headers=recruiter_headers)
    assert r.status_code == 201
    job = r.json()
    assert {"python", "django", "postgresql"} <= set(job["required_skills"])
    assert client.get(f"/jobs/{job['id']}", headers=recruiter_headers).json()["title"] == "Backend Developer"
    assert len(client.get("/jobs", headers=recruiter_headers).json()) == 1
    assert client.post("/jobs", json={"title": "x", "description": "short"}, headers=recruiter_headers).status_code == 422
    assert client.get("/jobs/999", headers=recruiter_headers).status_code == 404
    assert client.delete(f"/jobs/{job['id']}", headers=admin_headers).status_code == 200


def test_job_upload_txt_and_pdf(client, recruiter_headers):
    r = client.post("/jobs/upload", data={"title": "Python Dev"},
                    files={"file": ("jd.txt", JOB_TEXT.encode(), "text/plain")}, headers=recruiter_headers)
    assert r.status_code == 201
    pdf = make_pdf([JOB_TEXT[:80], JOB_TEXT[80:]])
    r = client.post("/jobs/upload", data={"title": "Python Dev 2"},
                    files={"file": ("jd.pdf", pdf, "application/pdf")}, headers=recruiter_headers)
    assert r.status_code == 201
    r = client.post("/jobs/upload", data={"title": "Bad"},
                    files={"file": ("jd.exe", b"x", "application/octet-stream")}, headers=recruiter_headers)
    assert r.status_code == 400


def test_candidate_list_get_and_skill_filter(client, uploaded):
    h = uploaded["headers"]
    assert len(client.get("/candidates", headers=h).json()) == 2
    assert len(client.get("/candidates?skill=nmap", headers=h).json()) == 1
    cand = client.get(f"/candidates/{uploaded['candidates'][0]}", headers=h).json()
    assert cand["name"] == "Priya Sharma"
    assert client.get("/candidates/9999", headers=h).status_code == 404


def test_candidate_search_endpoint(client, uploaded):
    r = client.post("/candidates/search", json={"query": "Docker AWS backend"}, headers=uploaded["headers"])
    assert r.status_code == 200 and r.json()["count"] >= 1


def test_match_endpoint_scores_correctly(client, uploaded):
    h, job = uploaded["headers"], uploaded["job"]
    priya, rahul = uploaded["candidates"]
    good = client.post("/analysis/match", json={"candidate_id": priya, "job_id": job}, headers=h).json()
    bad = client.post("/analysis/match", json={"candidate_id": rahul, "job_id": job}, headers=h).json()
    assert good["match_score"] > bad["match_score"]
    assert "python" in good["matched_skills"] and "python" in bad["missing_skills"]
    assert good["llm_used"] is False and good["warnings"]  # fallback is flagged, not silent


def test_summary_questions_compare_job_analysis(client, uploaded):
    h, job = uploaded["headers"], uploaded["job"]
    priya, rahul = uploaded["candidates"]
    s = client.post("/analysis/summary", json={"candidate_id": priya, "job_id": job}, headers=h)
    assert s.status_code == 200 and "Priya" in s.json()["summary"]
    q = client.post("/analysis/questions", json={"candidate_id": rahul, "job_id": job, "num_questions": 5}, headers=h)
    assert q.status_code == 200 and "1." in q.json()["questions"]
    c = client.post("/analysis/compare", json={"candidate_ids": [priya, rahul], "job_id": job}, headers=h).json()
    assert c["ranking"][0]["candidate_id"] == priya and c["ranking"][0]["rank"] == 1
    j = client.get(f"/analysis/job/{job}", headers=h).json()
    assert "python" in j["required_skills"] and j["min_years_experience"] == 3


def test_analysis_errors(client, uploaded):
    h = uploaded["headers"]
    assert client.post("/analysis/match", json={"candidate_id": 999, "job_id": uploaded["job"]}, headers=h).status_code == 404
    assert client.post("/analysis/match", json={"candidate_id": 1, "job_id": 999}, headers=h).status_code == 404
    assert client.post("/analysis/compare", json={"candidate_ids": [1]}, headers=h).status_code == 422
    assert client.post("/analysis/compare", json={"candidate_ids": [1, 1]}, headers=h).status_code == 400
    assert client.post("/analysis/questions", json={"candidate_id": 1, "num_questions": 99}, headers=h).status_code == 422


def test_admin_stats_and_audit(client, uploaded, admin_headers):
    stats = client.get("/dashboard/stats", headers=admin_headers).json()
    assert stats["candidates"] == 2 and stats["jobs"] == 1 and stats["top_skills"]
    actions = {e["action"] for e in client.get("/admin/audit", headers=admin_headers).json()}
    assert {"upload_resume", "create_job", "login"} <= actions
