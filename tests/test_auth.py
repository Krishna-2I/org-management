from tests.conftest import auth_headers, login, register_org


def test_wrong_password_returns_401(client):
    register_org(client)
    response = client.post("/api/v1/auth/login", data={"username": "owner@acmecorp.io", "password": "wrong"})
    assert response.status_code == 401


def test_no_token_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_garbage_token_returns_401(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_refresh_rotates_token(owner_session):
    client, headers, tokens = owner_session
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


def test_reusing_old_refresh_token_revokes_family(owner_session):
    client, headers, tokens = owner_session
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    new_tokens = first.json()

    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401

    blocked = client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert blocked.status_code == 401


def test_logout_blacklists_access_token(owner_session):
    client, headers, tokens = owner_session
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers)
    assert logout.status_code == 204

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 401


def test_change_password_revokes_refresh_tokens(owner_session):
    client, headers, tokens = owner_session
    response = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "ownerpass123", "new_password": "newpassword123"},
        headers=headers,
    )
    assert response.status_code == 204

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401

    new_login = login(client, "owner@acmecorp.io", "newpassword123")
    assert "access_token" in new_login
