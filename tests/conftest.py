import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("FERNET_KEYS", "zxU7Qk0qfD9Vq1b8mF5r2jT3hN6pL4sC8wY0xA1vB2c=")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core import cache as cache_module
from app.db.session import Base, get_db
from app.main import app


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def exists(self, key):
        return 1 if key in self.store else 0

    def delete(self, key):
        self.store.pop(key, None)

    def scan_iter(self, match=None):
        prefix = match[:-1] if match and match.endswith("*") else match
        return [k for k in list(self.store) if prefix is None or k.startswith(prefix)]


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    monkeypatch.setattr(cache_module, "_client", FakeRedis())


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_org(client, org_name="Acme", owner_email="owner@acmecorp.io", password="ownerpass123"):
    response = client.post(
        "/api/v1/organizations/register",
        json={"org_name": org_name, "owner_name": "Owner One", "owner_email": owner_email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client, email, password):
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_session(client):
    register_org(client)
    tokens = login(client, "owner@acmecorp.io", "ownerpass123")
    return client, auth_headers(tokens["access_token"]), tokens


@pytest.fixture()
def org_with_roles(client):
    register_org(client)
    owner_tokens = login(client, "owner@acmecorp.io", "ownerpass123")
    owner_headers = auth_headers(owner_tokens["access_token"])

    dept = client.post("/api/v1/departments", json={"name": "Engineering"}, headers=owner_headers)
    assert dept.status_code == 201, dept.text
    department_id = dept.json()["id"]

    manager = client.post(
        "/api/v1/users",
        json={
            "email": "manager@acmecorp.io",
            "full_name": "Mana Ger",
            "password": "managerpass123",
            "role": "manager",
            "department_id": department_id,
        },
        headers=owner_headers,
    )
    assert manager.status_code == 201, manager.text
    manager_tokens = login(client, "manager@acmecorp.io", "managerpass123")
    manager_headers = auth_headers(manager_tokens["access_token"])

    employee = client.post(
        "/api/v1/users",
        json={
            "email": "employee@acmecorp.io",
            "full_name": "Emp Loyee",
            "password": "employeepass123",
            "role": "employee",
            "department_id": department_id,
        },
        headers=owner_headers,
    )
    assert employee.status_code == 201, employee.text
    employee_tokens = login(client, "employee@acmecorp.io", "employeepass123")
    employee_headers = auth_headers(employee_tokens["access_token"])

    return {
        "client": client,
        "department_id": department_id,
        "owner_headers": owner_headers,
        "manager_headers": manager_headers,
        "manager_id": manager.json()["id"],
        "employee_headers": employee_headers,
        "employee_id": employee.json()["id"],
    }
