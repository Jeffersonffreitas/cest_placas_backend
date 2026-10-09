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
    client: TestClient, headers: dict[str, str], *, direction: str, name: str
) -> dict[str, object]:
    response = client.post(
        "/api/v1/access-points",
        json={
            "name": name,
            "code": name.upper().replace(" ", "_"),
            "direction": direction,
            "description": f"Ponto {direction}",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("direction", ("ENTRADA", "SAIDA", "MISTO"))
def test_create_access_point_for_each_direction(
    client: TestClient, direction: str
) -> None:
    body = _create_access_point(
        client, _admin_headers(client), direction=direction, name=f"Portao {direction}"
    )
    assert body["direction"] == direction
    assert body["is_active"] is True
    assert isinstance(body["id"], int)


def test_access_point_rejects_invalid_direction(client: TestClient) -> None:
    response = client.post(
        "/api/v1/access-points",
        json={"name": "Portao invalido", "direction": "LATERAL"},
        headers=_admin_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_list_get_filter_update_and_logically_deactivate_access_point(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    entrance = _create_access_point(
        client, headers, direction="ENTRADA", name="Portao Principal"
    )
    _create_access_point(client, headers, direction="SAIDA", name="Portao Fundos")

    listing = client.get(
        "/api/v1/access-points?active=true&direction=ENTRADA&name=principal",
        headers=headers,
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [entrance["id"]]

    detail = client.get(
        f"/api/v1/access-points/{entrance['id']}", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["name"] == "Portao Principal"

    updated = client.put(
        f"/api/v1/access-points/{entrance['id']}",
        json={"name": "Guarita Principal", "direction": "MISTO"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Guarita Principal"
    assert updated.json()["direction"] == "MISTO"

    deleted = client.delete(
        f"/api/v1/access-points/{entrance['id']}", headers=headers
    )
    assert deleted.status_code == 204
    persisted = client.get(
        f"/api/v1/access-points/{entrance['id']}", headers=headers
    )
    assert persisted.status_code == 200
    assert persisted.json()["is_active"] is False


@pytest.mark.parametrize(
    ("method", "path", "json"),
    (
        ("get", "/api/v1/access-points", None),
        ("get", "/api/v1/access-points/1", None),
        ("post", "/api/v1/access-points", {"name": "P", "direction": "MISTO"}),
        ("put", "/api/v1/access-points/1", {"name": "P"}),
        ("delete", "/api/v1/access-points/1", None),
    ),
)
def test_access_point_endpoints_require_authentication(
    client: TestClient, method: str, path: str, json: dict | None
) -> None:
    response = client.request(method, path, json=json)
    assert response.status_code == 401


def test_access_point_pagination_validation(client: TestClient) -> None:
    headers = _admin_headers(client)
    assert client.get(
        "/api/v1/access-points?skip=-1", headers=headers
    ).status_code == 422
    assert client.get(
        "/api/v1/access-points?limit=0", headers=headers
    ).status_code == 422
    assert client.get(
        "/api/v1/access-points?limit=101", headers=headers
    ).status_code == 422
