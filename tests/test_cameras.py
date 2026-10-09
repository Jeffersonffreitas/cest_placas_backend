import pytest
from fastapi.testclient import TestClient


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_access_point(
    client: TestClient, headers: dict[str, str], name: str = "Portao Principal"
) -> dict[str, object]:
    response = client.post(
        "/api/v1/access-points",
        json={"name": name, "direction": "ENTRADA"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_camera(
    client: TestClient, headers: dict[str, str], access_point_id: int,
    code: str = "CAM-PRINCIPAL",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/cameras",
        json={
            "access_point_id": access_point_id,
            "name": "Camera Portao Principal",
            "code": code,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_camera_crud_link_filter_update_and_logical_deactivation(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    point = _create_access_point(client, headers)
    other_point = _create_access_point(client, headers, "Portao Fundos")
    camera = _create_camera(client, headers, int(point["id"]))

    assert camera["access_point_id"] == point["id"]
    detail = client.get(f"/api/v1/cameras/{camera['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["code"] == "CAM-PRINCIPAL"

    listing = client.get(
        f"/api/v1/cameras?access_point_id={point['id']}&active=true&name=principal",
        headers=headers,
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [camera["id"]]
    empty = client.get(
        f"/api/v1/cameras?access_point_id={other_point['id']}", headers=headers
    )
    assert empty.json() == []

    updated = client.put(
        f"/api/v1/cameras/{camera['id']}",
        json={
            "access_point_id": other_point["id"],
            "name": "Camera Fundos",
            "code": "cam-fundos",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["access_point_id"] == other_point["id"]
    assert updated.json()["code"] == "CAM-FUNDOS"

    deleted = client.delete(f"/api/v1/cameras/{camera['id']}", headers=headers)
    assert deleted.status_code == 204
    persisted = client.get(f"/api/v1/cameras/{camera['id']}", headers=headers)
    assert persisted.json()["is_active"] is False


def test_camera_rejects_missing_or_inactive_access_point(client: TestClient) -> None:
    headers = _admin_headers(client)
    missing = client.post(
        "/api/v1/cameras",
        json={"access_point_id": 999999, "name": "Camera", "code": "CAM-X"},
        headers=headers,
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "access_point_not_found"

    point = _create_access_point(client, headers)
    assert client.delete(
        f"/api/v1/access-points/{point['id']}", headers=headers
    ).status_code == 204
    inactive = client.post(
        "/api/v1/cameras",
        json={"access_point_id": point["id"], "name": "Camera", "code": "CAM-Y"},
        headers=headers,
    )
    assert inactive.status_code == 422
    assert inactive.json()["error"]["code"] == "inactive_access_point"

    inactive_camera = client.post(
        "/api/v1/cameras",
        json={
            "access_point_id": point["id"],
            "name": "Camera inativa",
            "code": "CAM-Z",
            "is_active": False,
        },
        headers=headers,
    )
    assert inactive_camera.status_code == 201
    assert inactive_camera.json()["is_active"] is False


def test_camera_code_is_unique(client: TestClient) -> None:
    headers = _admin_headers(client)
    point = _create_access_point(client, headers)
    _create_camera(client, headers, int(point["id"]), "CAM-UNICA")
    duplicate = client.post(
        "/api/v1/cameras",
        json={
            "access_point_id": point["id"],
            "name": "Outra camera",
            "code": "cam-unica",
        },
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "camera_code_conflict"


@pytest.mark.parametrize(
    ("method", "path", "json"),
    (
        ("get", "/api/v1/cameras", None),
        ("get", "/api/v1/cameras/1", None),
        (
            "post", "/api/v1/cameras",
            {"access_point_id": 1, "name": "C", "code": "C-1"},
        ),
        ("put", "/api/v1/cameras/1", {"name": "C"}),
        ("delete", "/api/v1/cameras/1", None),
    ),
)
def test_camera_endpoints_require_authentication(
    client: TestClient, method: str, path: str, json: dict | None
) -> None:
    assert client.request(method, path, json=json).status_code == 401
