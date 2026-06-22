from fastapi.testclient import TestClient


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_student(
    client: TestClient,
    headers: dict[str, str],
    registration_number: str = "20260001",
    full_name: str = "Maria Silva",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/students",
        json={
            "registration_number": registration_number,
            "full_name": full_name,
            "email": f"{registration_number}@example.com",
            "phone": "85999990000",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_vehicle(
    client: TestClient,
    headers: dict[str, str],
    student_id: int,
    plate: str = "abc-1234",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_id,
            "plate": plate,
            "brand": "Fiat",
            "model": "Mobi",
            "color": "Branco",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_students_crud_requires_admin_paginates_and_deactivates(client: TestClient) -> None:
    response = client.post(
        "/api/v1/students",
        json={
            "registration_number": "20260001",
            "full_name": "Maria Silva",
        },
    )
    assert response.status_code == 401

    headers = _admin_headers(client)
    first_student = _create_student(client, headers, "20260001", "Maria Silva")
    second_student = _create_student(client, headers, "20260002", "Joao Pereira")

    response = client.get("/api/v1/students?skip=1&limit=1", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second_student["id"]]

    response = client.get(f"/api/v1/students/{first_student['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["registration_number"] == "20260001"

    response = client.get("/api/v1/students/by-registration/20260002", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == second_student["id"]

    response = client.put(
        f"/api/v1/students/{first_student['id']}",
        json={"phone": "85888880000"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "85888880000"

    response = client.delete(f"/api/v1/students/{first_student['id']}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/students/{first_student['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_duplicate_active_registration_number_is_rejected(client: TestClient) -> None:
    headers = _admin_headers(client)
    _create_student(client, headers, "20260001", "Maria Silva")

    response = client.post(
        "/api/v1/students",
        json={
            "registration_number": "20260001",
            "full_name": "Maria Silva Duplicada",
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "student_registration_number_conflict"


def test_vehicle_crud_links_active_student_normalizes_paginates_and_deactivates(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)
    student_id = int(student["id"])

    first_vehicle = _create_vehicle(client, headers, student_id, "abc-1234")
    assert first_vehicle["student_id"] == student_id
    assert first_vehicle["plate"] == "ABC1234"

    second_vehicle = _create_vehicle(client, headers, student_id, "qwe1r23")

    response = client.get(
        f"/api/v1/vehicles?student_id={student_id}&skip=1&limit=1",
        headers=headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second_vehicle["id"]]

    response = client.get("/api/v1/vehicles/by-plate/abc-1234", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == first_vehicle["id"]
    assert response.json()["plate"] == "ABC1234"

    response = client.get(f"/api/v1/vehicles/{first_vehicle['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == first_vehicle["id"]

    response = client.put(
        f"/api/v1/vehicles/{first_vehicle['id']}",
        json={"color": "Preto", "plate": "abc1d23"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["color"] == "Preto"
    assert response.json()["plate"] == "ABC1D23"

    response = client.delete(f"/api/v1/vehicles/{second_vehicle['id']}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/vehicles/{second_vehicle['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_duplicate_active_plate_is_rejected_after_normalization(client: TestClient) -> None:
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


def test_vehicle_rejects_invalid_plate_and_inactive_student(client: TestClient) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)

    invalid_plate_response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student["id"], "plate": "ABC"},
        headers=headers,
    )
    assert invalid_plate_response.status_code == 400
    assert invalid_plate_response.json()["error"]["code"] == "invalid_plate"

    deactivate_response = client.delete(f"/api/v1/students/{student['id']}", headers=headers)
    assert deactivate_response.status_code == 204

    inactive_student_response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student["id"], "plate": "ABC1234"},
        headers=headers,
    )
    assert inactive_student_response.status_code == 409
    assert inactive_student_response.json()["error"]["code"] == "student_inactive"


def test_vehicle_update_rejects_inactive_student_target(client: TestClient) -> None:
    headers = _admin_headers(client)
    active_student = _create_student(client, headers, "20260001", "Maria Silva")
    inactive_student = _create_student(client, headers, "20260002", "Joao Pereira")
    vehicle = _create_vehicle(client, headers, int(active_student["id"]), "ABC1234")

    response = client.delete(f"/api/v1/students/{inactive_student['id']}", headers=headers)
    assert response.status_code == 204

    response = client.put(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"student_id": inactive_student["id"]},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "student_inactive"
