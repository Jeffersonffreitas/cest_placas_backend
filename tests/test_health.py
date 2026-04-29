from fastapi.testclient import TestClient

from app.main import app


def test_health_route_returns_application_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "CEST Placas Backend",
        "version": "0.1.0",
        "environment": "local",
    }
