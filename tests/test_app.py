from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_active_app_endpoint_returns_expected_shape():
    response = client.get("/api/active-app")

    assert response.status_code == 200
    payload = response.json()
    assert "name" in payload
    assert "bundle_id" in payload
    assert "pid" in payload
    assert "platform" in payload
