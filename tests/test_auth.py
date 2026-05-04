from fastapi.testclient import TestClient


def test_login_returns_bearer_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong_password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_me_returns_authenticated_user(client: TestClient) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    user = response.json()["user"]
    assert user["username"] == "admin"
    assert user["is_active"] is True
    assert user["is_superuser"] is True


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_login_validation_error_is_json_serializable(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_oauth2_password_flow_points_to_login(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    security_scheme = response.json()["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert security_scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/login"
