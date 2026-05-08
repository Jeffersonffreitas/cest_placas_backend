from fastapi.testclient import TestClient


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_student(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/v1/students",
        json={
            "registration_number": "20260001",
            "full_name": "Maria Silva",
            "email": "maria.silva@example.com",
            "phone": "85999990000",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_students_crud_requires_admin_and_deletes(client: TestClient) -> None:
    response = client.post(
        "/api/v1/students",
        json={
            "registration_number": "20260001",
            "full_name": "Maria Silva",
        },
    )
    assert response.status_code == 401

    headers = _admin_headers(client)
    student = _create_student(client, headers)
    student_id = student["id"]

    response = client.get("/api/v1/students", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["registration_number"] == "20260001"

    response = client.put(
        f"/api/v1/students/{student_id}",
        json={"phone": "85888880000", "is_active": False},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "85888880000"
    assert response.json()["is_active"] is False

    response = client.delete(f"/api/v1/students/{student_id}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/students/{student_id}", headers=headers)
    assert response.status_code == 404


def test_vehicle_crud_links_student_normalizes_and_searches_plate(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)
    student_id = student["id"]

    response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_id,
            "plate": "abc-1234",
            "brand": "Fiat",
            "model": "Mobi",
            "color": "Branco",
        },
        headers=headers,
    )
    assert response.status_code == 201
    vehicle = response.json()
    assert vehicle["student_id"] == student_id
    assert vehicle["plate"] == "ABC1234"

    response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_id,
            "plate": "qwe1r23",
            "brand": "Honda",
            "model": "Biz",
            "color": "Vermelha",
        },
        headers=headers,
    )
    assert response.status_code == 201
    second_vehicle = response.json()

    response = client.get(f"/api/v1/vehicles?student_id={student_id}", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get("/api/v1/vehicles/by-plate/abc-1234", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == vehicle["id"]
    assert response.json()["plate"] == "ABC1234"

    response = client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"color": "Preto"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["color"] == "Preto"

    response = client.delete(f"/api/v1/vehicles/{second_vehicle['id']}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/vehicles/{second_vehicle['id']}", headers=headers)
    assert response.status_code == 404


def test_duplicate_plate_is_rejected_after_normalization(client: TestClient) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)

    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student["id"], "plate": "ABC-1234"},
        headers=headers,
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student["id"], "plate": "abc1234"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vehicle_plate_conflict"


def test_student_with_linked_vehicle_cannot_be_deleted(client: TestClient) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)

    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student["id"], "plate": "ABC1234"},
        headers=headers,
    )
    assert response.status_code == 201

    response = client.delete(f"/api/v1/students/{student['id']}", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "student_has_vehicles"
