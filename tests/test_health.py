from fastapi.testclient import TestClient


def test_health_route_returns_application_status(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "CEST Placas Backend",
        "version": "0.1.0",
        "environment": "local",
    }
