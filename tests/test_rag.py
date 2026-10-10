from app.rag import vector_store
from app.services import candidate_service


def test_search_returns_relevant_candidate_first(client, uploaded):
    priya, rahul = uploaded["candidates"]
    results = candidate_service.search_candidates("Django REST API developer", top_k=2)
    assert results and results[0]["candidate_id"] == priya
    results = candidate_service.search_candidates("penetration testing Burp Suite", top_k=2)
    assert results[0]["candidate_id"] == rahul


def test_search_empty_database_returns_empty_list(client, recruiter_headers):
    r = client.post("/candidates/search", json={"query": "python developer"}, headers=recruiter_headers)
    assert r.status_code == 200
    assert r.json()["results"] == [] and r.json()["message"]


def test_chunks_are_stored_and_deleted(client, uploaded, admin_headers):
    cid = uploaded["candidates"][0]
    assert vector_store.get_candidate_chunks(cid)
    assert client.delete(f"/candidates/{cid}", headers=admin_headers).status_code == 200
    assert vector_store.get_candidate_chunks(cid) == []
    assert client.get(f"/candidates/{cid}", headers=admin_headers).status_code == 404


def test_search_restricted_to_candidate_ids(client, uploaded):
    priya, rahul = uploaded["candidates"]
    hits = vector_store.search_chunks("Python Django", top_k=5, candidate_ids=[rahul])
    assert hits and all(h["candidate_id"] == rahul for h in hits)


def test_search_validation(client, recruiter_headers):
    assert client.post("/candidates/search", json={"query": "a"}, headers=recruiter_headers).status_code == 422
