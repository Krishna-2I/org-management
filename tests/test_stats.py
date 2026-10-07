def test_employee_cannot_view_stats(org_with_roles):
    ctx = org_with_roles
    response = ctx["client"].get("/api/v1/stats/overview", headers=ctx["employee_headers"])
    assert response.status_code == 403


def test_owner_and_manager_see_different_scopes(org_with_roles):
    ctx = org_with_roles
    owner_view = ctx["client"].get("/api/v1/stats/overview", headers=ctx["owner_headers"]).json()
    manager_view = ctx["client"].get("/api/v1/stats/overview", headers=ctx["manager_headers"]).json()

    assert owner_view["users_by_role"]["owner"] == 1
    assert "owner" not in manager_view["users_by_role"]
    assert len(manager_view["departments"]) == 1
