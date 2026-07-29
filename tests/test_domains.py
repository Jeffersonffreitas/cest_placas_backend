from fastapi.testclient import TestClient


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "change_me"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_domain(
    client: TestClient, headers: dict[str, str], *, type: str = "COR_VEICULO",
    code: str | None = "BRANCO", name: str = "Branco",
    parent_id: int | None = None, is_active: bool = True,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/domains",
        json={
            "type": type, "code": code, "name": name,
            "parent_id": parent_id, "is_active": is_active,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_domain_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/domains").status_code == 401
    assert client.get("/api/v1/domains/1").status_code == 401
    assert client.post(
        "/api/v1/domains", json={"type": "CURSO", "name": "Direito"}
    ).status_code == 401
    assert client.put("/api/v1/domains/1", json={"name": "Direito"}).status_code == 401
    assert client.delete("/api/v1/domains/1").status_code == 401


def test_create_list_filter_get_update_and_deactivate_domain(client: TestClient) -> None:
    headers = _admin_headers(client)
    brand = _create_domain(
        client, headers, type="MARCA_VEICULO", code="FIAT", name="Fiat"
    )
    model = _create_domain(
        client, headers, type="MODELO_VEICULO", code="MOBI", name="Mobi",
        parent_id=int(brand["id"]),
    )
    inactive_color = _create_domain(
        client, headers, code="PRETO", name="Preto", is_active=False
    )

    response = client.get("/api/v1/domains?skip=0&limit=100", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 3

    response = client.get("/api/v1/domains?tipo=modelo_veiculo", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [model["id"]]

    response = client.get("/api/v1/domains?ativo=false", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [inactive_color["id"]]

    response = client.get(
        f"/api/v1/domains?parent_id={brand['id']}", headers=headers
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [model["id"]]

    response = client.get(f"/api/v1/domains/{brand['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["code"] == "FIAT"

    response = client.put(
        f"/api/v1/domains/{model['id']}", json={"name": "Mobi Like"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Mobi Like"

    response = client.delete(f"/api/v1/domains/{brand['id']}", headers=headers)
    assert response.status_code == 204
    response = client.get(f"/api/v1/domains/{brand['id']}", headers=headers)
    assert response.json()["is_active"] is False


def test_domain_validation_and_active_duplicate_protection(client: TestClient) -> None:
    headers = _admin_headers(client)
    assert client.post(
        "/api/v1/domains", json={"type": "  ", "name": "Fiat"}, headers=headers
    ).status_code == 422
    assert client.post(
        "/api/v1/domains", json={"type": "MARCA_VEICULO", "name": "  "}, headers=headers
    ).status_code == 422
    assert client.get("/api/v1/domains?limit=101", headers=headers).status_code == 422

    _create_domain(client, headers, type="CURSO", code="DIR", name="Direito")
    response = client.post(
        "/api/v1/domains",
        json={"type": "curso", "code": "dir", "name": "Outro Direito"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "domain_conflict"
