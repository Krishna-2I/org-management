def test_employee_cannot_create_task(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(
        "/api/v1/tasks", json={"title": "Do a thing"}, headers=ctx["employee_headers"]
    )
    assert response.status_code == 403


def test_manager_can_assign_task_in_own_department(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].post(
        "/api/v1/tasks",
        json={"title": "Write report", "assignee_id": ctx["employee_id"]},
        headers=ctx["manager_headers"],
    )
    assert response.status_code == 201


def test_employee_sees_only_assigned_tasks(org_with_roles):
    ctx = org_with_roles
    ctx["client"].post(
        "/api/v1/tasks",
        json={"title": "Not for you"},
        headers=ctx["owner_headers"],
    )
    ctx["client"].post(
        "/api/v1/tasks",
        json={"title": "For you", "assignee_id": ctx["employee_id"]},
        headers=ctx["owner_headers"],
    )

    response = ctx["client"].get("/api/v1/tasks", headers=ctx["employee_headers"])
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "For you"


def test_employee_can_update_status_of_own_task(org_with_roles):
    ctx = org_with_roles
    task = ctx["client"].post(
        "/api/v1/tasks",
        json={"title": "For you", "assignee_id": ctx["employee_id"]},
        headers=ctx["owner_headers"],
    ).json()

    response = ctx["client"].patch(
        f"/api/v1/tasks/{task['id']}/status", json={"status": "done"}, headers=ctx["employee_headers"]
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_employee_cannot_update_others_task_status(org_with_roles):
    ctx = org_with_roles
    task = ctx["client"].post(
        "/api/v1/tasks",
        json={"title": "Not yours"},
        headers=ctx["owner_headers"],
    ).json()

    response = ctx["client"].patch(
        f"/api/v1/tasks/{task['id']}/status", json={"status": "done"}, headers=ctx["employee_headers"]
    )
    assert response.status_code == 404
