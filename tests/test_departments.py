def test_employee_cannot_create_department(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(
        "/api/v1/departments", json={"name": "New Dept"}, headers=ctx["employee_headers"]
    )
    assert response.status_code == 403


def test_manager_cannot_create_department(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(
        "/api/v1/departments", json={"name": "New Dept"}, headers=ctx["manager_headers"]
    )
    assert response.status_code == 403


def test_delete_department_with_users_conflicts(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].delete(f"/api/v1/departments/{ctx['department_id']}", headers=ctx["owner_headers"])
    assert response.status_code == 409


def test_headcount_excludes_deactivated_users(org_with_roles):
    ctx = org_with_roles
    before = ctx["client"].get("/api/v1/departments/headcount", headers=ctx["owner_headers"]).json()
    department = next(d for d in before if d["id"] == ctx["department_id"])
    assert department["headcount"] == 2

    ctx["client"].post(f"/api/v1/users/{ctx['employee_id']}/deactivate", headers=ctx["owner_headers"])

    after = ctx["client"].get("/api/v1/departments/headcount", headers=ctx["owner_headers"]).json()
    department = next(d for d in after if d["id"] == ctx["department_id"])
    assert department["headcount"] == 1


def test_pagination_math(owner_session):
    client, headers, tokens = owner_session
    for i in range(5):
        client.post("/api/v1/departments", json={"name": f"Dept {i}"}, headers=headers)

    response = client.get("/api/v1/departments?page=2&size=2", headers=headers)
    data = response.json()
    assert data["page"] == 2
    assert data["size"] == 2
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3
