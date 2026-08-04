import pytest
from fastapi.testclient import TestClient


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "change_me"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _student(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/students",
        json={"registration_number": "20269999", "full_name": "Teste Veiculo"},
        headers=headers,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _domain(
    client: TestClient, headers: dict[str, str], domain_type: str, name: str
) -> int:
    response = client.post(
        "/api/v1/domains",
        json={"type": domain_type, "name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_vehicle_accepts_domain_ids_and_returns_names(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    brand_id = _domain(client, headers, "MARCA_VEICULO", "Honda")
    model_id = _domain(client, headers, "MODELO_VEICULO", "City")
    color_id = _domain(client, headers, "COR_VEICULO", "Prata")

    response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_id,
            "plate": "BRA2E19",
            "brand_id": brand_id,
            "model_id": model_id,
            "color_id": color_id,
        },
        headers=headers,
    )
    assert response.status_code == 201
    vehicle = response.json()
    assert (vehicle["brand_id"], vehicle["model_id"], vehicle["color_id"]) == (
        brand_id, model_id, color_id,
    )
    assert (vehicle["brand_name"], vehicle["model_name"], vehicle["color_name"]) == (
        "Honda", "City", "Prata",
    )
    assert (vehicle["brand"], vehicle["model"], vehicle["color"]) == (
        "Honda", "City", "Prata",
    )

    listed = client.get("/api/v1/vehicles", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["brand_id"] == brand_id
    assert listed.json()[0]["brand_name"] == "Honda"


def test_vehicle_text_fields_create_and_link_domains_compatibly(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_id,
            "plate": "ABC1D23",
            "brand": "Fiat",
            "model": "Mobi",
            "color": "Branco",
        },
        headers=headers,
    )
    assert response.status_code == 201
    vehicle = response.json()
    assert (vehicle["brand"], vehicle["model"], vehicle["color"]) == (
        "Fiat", "Mobi", "Branco",
    )
    assert all(vehicle[field] is not None for field in ("brand_id", "model_id", "color_id"))
    assert (vehicle["brand_name"], vehicle["model_name"], vehicle["color_name"]) == (
        "Fiat", "Mobi", "Branco",
    )

    by_plate = client.get("/api/v1/vehicles/by-plate/abc-1d23", headers=headers)
    assert by_plate.status_code == 200
    assert by_plate.json()["id"] == vehicle["id"]


@pytest.mark.parametrize("field", ["brand_id", "model_id", "color_id"])
def test_vehicle_rejects_missing_domain_id(client: TestClient, field: str) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student_id, "plate": "XYZ9Z99", field: 999999},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == f"invalid_{field}"


def test_vehicle_domain_fields_remain_protected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": 1, "plate": "ABC1D23", "brand_id": 1},
    )
    assert response.status_code == 401
