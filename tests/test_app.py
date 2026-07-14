from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


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


def test_cors_origin_is_configured_from_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://dashboard.example.com,https://admin.example.com",
    )

    app = main_module.create_app()
    test_client = TestClient(app)
    response = test_client.options(
        "/health",
        headers={
            "Origin": "https://dashboard.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://dashboard.example.com"
