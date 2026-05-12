from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent


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
            "registration_number": "20260002",
            "full_name": "Joao Pereira",
            "email": "joao.pereira@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_manual_plate_read_matches_vehicle_and_registers_access_event(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)

    vehicle_response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student["id"],
            "plate": "abc-1d23",
            "brand": "Fiat",
            "model": "Mobi",
            "color": "Branco",
        },
        headers=headers,
    )
    assert vehicle_response.status_code == 201
    vehicle = vehicle_response.json()

    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": " abc-1d23 "},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["plate_input"] == "abc-1d23"
    assert body["plate_normalized"] == "ABC1D23"
    assert body["source"] == "manual"
    assert body["status"] == "matched"
    assert body["vehicle"]["id"] == vehicle["id"]
    assert body["student"]["id"] == student["id"]

    access_event = db_session.scalars(select(AccessEvent)).one()
    assert access_event.plate_input == "abc-1d23"
    assert access_event.plate_normalized == "ABC1D23"
    assert access_event.vehicle_id == vehicle["id"]
    assert access_event.student_id == student["id"]
    assert access_event.status == "matched"


def test_manual_plate_read_not_found_registers_access_event(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)

    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "zzz-9z99"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["plate_input"] == "zzz-9z99"
    assert body["plate_normalized"] == "ZZZ9Z99"
    assert body["status"] == "not_found"
    assert body["vehicle"] is None
    assert body["student"] is None

    access_event = db_session.scalars(select(AccessEvent)).one()
    assert access_event.plate_input == "zzz-9z99"
    assert access_event.plate_normalized == "ZZZ9Z99"
    assert access_event.vehicle_id is None
    assert access_event.student_id is None
    assert access_event.source == "manual"
    assert access_event.status == "not_found"


def test_manual_plate_read_requires_admin(client: TestClient) -> None:
    response = client.post("/api/v1/plates/read-manual", json={"plate": "ABC1D23"})

    assert response.status_code == 401


def test_manual_plate_read_rejects_invalid_plate(client: TestClient) -> None:
    headers = _admin_headers(client)

    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "ABC"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_plate"
