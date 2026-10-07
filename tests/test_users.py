def test_employee_cannot_create_user(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(
        "/api/v1/users",
        json={"email": "new@acmecorp.io", "full_name": "New Person", "password": "password123", "role": "employee"},
        headers=ctx["employee_headers"],
    )
    assert response.status_code == 403


def test_manager_can_only_create_employees_in_own_department(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(
        "/api/v1/users",
        json={"email": "new@acmecorp.io", "full_name": "New Person", "password": "password123", "role": "manager"},
        headers=ctx["manager_headers"],
    )
    assert response.status_code == 403


def test_manager_cannot_view_user_outside_department(org_with_roles):
    ctx = org_with_roles
    other_dept = ctx["client"].post("/api/v1/departments", json={"name": "Sales"}, headers=ctx["owner_headers"])
    assert other_dept.status_code == 201

    outsider = ctx["client"].post(
        "/api/v1/users",
        json={
            "email": "outsider@acmecorp.io",
            "full_name": "Out Sider",
            "password": "password123",
            "role": "employee",
            "department_id": other_dept.json()["id"],
        },
        headers=ctx["owner_headers"],
    )
    assert outsider.status_code == 201

    response = ctx["client"].get(f"/api/v1/users/{outsider.json()['id']}", headers=ctx["manager_headers"])
    assert response.status_code == 404


def test_owner_can_view_any_user(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].get(f"/api/v1/users/{ctx['employee_id']}", headers=ctx["owner_headers"])
    assert response.status_code == 200


def test_user_from_other_org_gets_404(client):
    from tests.conftest import auth_headers, login, register_org

    register_org(client, org_name="Org A", owner_email="a@orgatest.io", password="passwordA123")
    register_org(client, org_name="Org B", owner_email="b@orgbtest.io", password="passwordB123")

    a_tokens = login(client, "a@orgatest.io", "passwordA123")
    b_tokens = login(client, "b@orgbtest.io", "passwordB123")

    b_user = client.get("/api/v1/auth/me", headers=auth_headers(b_tokens["access_token"])).json()
    response = client.get(f"/api/v1/users/{b_user['id']}", headers=auth_headers(a_tokens["access_token"]))
    assert response.status_code == 404


def test_cannot_demote_last_owner(owner_session):
    client, headers, tokens = owner_session
    me = client.get("/api/v1/auth/me", headers=headers).json()
    response = client.patch(f"/api/v1/users/{me['id']}/role", json={"role": "manager"}, headers=headers)
    assert response.status_code == 400


def test_user_cannot_deactivate_self(owner_session):
    client, headers, tokens = owner_session
    me = client.get("/api/v1/auth/me", headers=headers).json()
    response = client.post(f"/api/v1/users/{me['id']}/deactivate", headers=headers)
    assert response.status_code == 400


def test_deactivated_user_token_stops_working(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(f"/api/v1/users/{ctx['employee_id']}/deactivate", headers=ctx["owner_headers"])
    assert response.status_code == 200

    me = ctx["client"].get("/api/v1/auth/me", headers=ctx["employee_headers"])
    assert me.status_code == 401


def test_invalid_sort_field_returns_400(owner_session):
    client, headers, tokens = owner_session
    response = client.get("/api/v1/users?sort_by=hashed_password", headers=headers)
    assert response.status_code == 400
    assert "allowed" in response.json()["error"]["details"]
