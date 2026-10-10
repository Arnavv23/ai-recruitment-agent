def test_login_success_and_me(client, admin_headers):
    r = client.get("/auth/me", headers=admin_headers)
    assert r.status_code == 200 and r.json()["role"] == "admin"


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_missing_and_invalid_token(client):
    assert client.get("/candidates").status_code == 401
    assert client.get("/candidates", headers={"Authorization": "Bearer fake.token.here"}).status_code == 401


def test_recruiter_cannot_manage_users(client, recruiter_headers):
    assert client.get("/admin/users", headers=recruiter_headers).status_code == 403
    r = client.post("/admin/users", json={"username": "x_user", "password": "Password123", "role": "admin"},
                    headers=recruiter_headers)
    assert r.status_code == 403


def test_recruiter_cannot_delete_candidate_or_job(client, uploaded):
    h = uploaded["headers"]
    assert client.delete(f"/candidates/{uploaded['candidates'][0]}", headers=h).status_code == 403
    assert client.delete(f"/jobs/{uploaded['job']}", headers=h).status_code == 403


def test_admin_can_create_user_and_delete_candidate(client, admin_headers, uploaded):
    r = client.post("/admin/users", json={"username": "new_rec", "password": "Password123", "role": "recruiter"},
                    headers=admin_headers)
    assert r.status_code == 201
    assert client.post("/admin/users", json={"username": "new_rec", "password": "Password123"},
                       headers=admin_headers).status_code == 409
    assert client.delete(f"/candidates/{uploaded['candidates'][0]}", headers=admin_headers).status_code == 200


def test_admin_cannot_delete_self_or_weak_password(client, admin_headers):
    me = client.get("/auth/me", headers=admin_headers).json()
    assert client.delete(f"/admin/users/{me['id']}", headers=admin_headers).status_code == 403
    r = client.post("/admin/users", json={"username": "weakone", "password": "short", "role": "recruiter"},
                    headers=admin_headers)
    assert r.status_code == 400


def test_role_comes_from_database_not_token(client, admin_headers):
    """Deleting the user invalidates their token even though it is still validly signed."""
    client.post("/admin/users", json={"username": "temp_user", "password": "Password123"}, headers=admin_headers)
    tok = client.post("/auth/login", json={"username": "temp_user", "password": "Password123"}).json()
    uid = tok["user"]["id"]
    client.delete(f"/admin/users/{uid}", headers=admin_headers)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {tok['access_token']}"}).status_code == 401
