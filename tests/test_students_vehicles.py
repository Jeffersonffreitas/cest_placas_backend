from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.person_vehicle import PersonVehicle


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


def test_vehicle_can_be_created_without_person_or_student(
    client: TestClient, db_session: Session,
) -> None:
    headers = _admin_headers(client)
    response = client.post(
        "/api/v1/vehicles", json={"plate": "SEM1D23"}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["student_id"] is None
    vehicle_id = int(response.json()["id"])
    assert db_session.scalars(
        select(PersonVehicle).where(PersonVehicle.vehicle_id == vehicle_id)
    ).first() is None
    assert "intalunoid" not in {
        column["name"] for column in inspect(db_session.bind).get_columns("tblveiculos")
    }


def test_vehicle_person_id_creates_link_and_navigation_works(
    client: TestClient, db_session: Session,
) -> None:
    headers = _admin_headers(client)
    person_response = client.post(
        "/api/v1/people",
        json={
            "person_type": "FUNCIONARIO",
            "registration_number": "FUN100",
            "full_name": "Funcionario Vinculado",
        },
        headers=headers,
    )
    assert person_response.status_code == 201
    person_id = int(person_response.json()["id"])

    response = client.post(
        "/api/v1/vehicles",
        json={"person_id": person_id, "plate": "FUN1A23"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["student_id"] is None
    vehicle_id = int(response.json()["id"])
    link = db_session.scalars(
        select(PersonVehicle).where(
            PersonVehicle.person_id == person_id,
            PersonVehicle.vehicle_id == vehicle_id,
        )
    ).one()
    assert link.is_active is True

    owners = client.get(f"/api/v1/vehicles/{vehicle_id}/owners", headers=headers)
    assert owners.status_code == 200
    assert [owner["id"] for owner in owners.json()] == [person_id]
    vehicles = client.get(f"/api/v1/people/{person_id}/vehicles", headers=headers)
    assert vehicles.status_code == 200
    assert [vehicle["id"] for vehicle in vehicles.json()] == [vehicle_id]


def test_vehicle_student_id_creates_compatibility_link(
    client: TestClient, db_session: Session,
) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers, "20260100", "Aluno Vinculado")
    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student["id"], "plate": "ALU1A23"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["student_id"] == student["id"]
    link = db_session.scalars(
        select(PersonVehicle).where(
            PersonVehicle.person_id == student["id"],
            PersonVehicle.vehicle_id == response.json()["id"],
        )
    ).one()
    assert link.is_active is True


def test_vehicle_rejects_missing_and_inactive_person(client: TestClient) -> None:
    headers = _admin_headers(client)
    missing = client.post(
        "/api/v1/vehicles",
        json={"person_id": 999999, "plate": "MIS1A23"},
        headers=headers,
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "person_not_found"

    person = client.post(
        "/api/v1/people",
        json={
            "person_type": "VISITANTE",
            "registration_number": "VIS100",
            "full_name": "Visitante Inativo",
        },
        headers=headers,
    ).json()
    assert client.delete(f"/api/v1/people/{person['id']}", headers=headers).status_code == 204
    inactive = client.post(
        "/api/v1/vehicles",
        json={"person_id": person["id"], "plate": "INA1A23"},
        headers=headers,
    )
    assert inactive.status_code == 409
    assert inactive.json()["error"]["code"] == "person_inactive"


def test_vehicle_rejects_missing_student_and_link_to_inactive_vehicle(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    missing_student = client.post(
        "/api/v1/vehicles",
        json={"student_id": 999999, "plate": "MIS2A34"},
        headers=headers,
    )
    assert missing_student.status_code == 404
    assert missing_student.json()["error"]["code"] == "student_not_found"

    person = client.post(
        "/api/v1/people",
        json={
            "person_type": "FUNCIONARIO",
            "registration_number": "FUN200",
            "full_name": "Funcionario Ativo",
        },
        headers=headers,
    ).json()
    inactive_vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "person_id": person["id"],
            "plate": "INA2A34",
            "is_active": False,
        },
        headers=headers,
    )
    assert inactive_vehicle.status_code == 409
    assert inactive_vehicle.json()["error"]["code"] == "vehicle_inactive"
