from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_frontend():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Org Manager" in response.text
