from tests.conftest import auth_headers, login, register_org


def test_register_creates_owner(client):
    data = register_org(client)
    assert data["role"] == "owner"
    assert data["email"] == "owner@acmecorp.io"


def test_duplicate_email_is_rejected(client):
    register_org(client)
    response = client.post(
        "/api/v1/organizations/register",
        json={
            "org_name": "Other Org",
            "owner_name": "Someone",
            "owner_email": "owner@acmecorp.io",
            "password": "anotherpass123",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_get_my_organization(client):
    register_org(client)
    tokens = login(client, "owner@acmecorp.io", "ownerpass123")
    response = client.get("/api/v1/organizations/me", headers=auth_headers(tokens["access_token"]))
    assert response.status_code == 200
    assert response.json()["name"] == "Acme"


def test_every_response_has_request_id_header(client):
    response = client.get("/health")
    assert "x-request-id" in {k.lower() for k in response.headers.keys()}
