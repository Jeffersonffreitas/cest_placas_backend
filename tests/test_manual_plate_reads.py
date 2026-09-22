from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.plate_read import PlateRead


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
    assert body["status"] == "ACESSO_LIBERADO"
    assert body["operational_decision"] == "ACESSO_LIBERADO"
    assert body["access_event_id"] == body["id"]
    assert isinstance(body["plate_read_id"], int)
    assert body["vehicle"]["id"] == vehicle["id"]
    assert body["student"]["id"] == student["id"]

    access_event = db_session.scalars(select(AccessEvent)).one()
    assert access_event.plate_input == "abc-1d23"
    assert access_event.plate_normalized == "ABC1D23"
    assert access_event.vehicle_id == vehicle["id"]
    assert access_event.student_id == student["id"]
    assert access_event.status == "ACESSO_LIBERADO"
    plate_read = db_session.scalars(select(PlateRead)).one()
    assert access_event.plate_read_id == plate_read.id
    assert plate_read.vehicle_id == vehicle["id"]
    assert plate_read.source == "manual"


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
    assert body["status"] == "VEICULO_NAO_CADASTRADO"
    assert body["operational_decision"] == "VEICULO_NAO_CADASTRADO"
    assert body["vehicle"] is None
    assert body["student"] is None

    access_event = db_session.scalars(select(AccessEvent)).one()
    assert access_event.plate_input == "zzz-9z99"
    assert access_event.plate_normalized == "ZZZ9Z99"
    assert access_event.vehicle_id is None
    assert access_event.student_id is None
    assert access_event.source == "manual"
    assert access_event.status == "VEICULO_NAO_CADASTRADO"


def test_manual_plate_read_requires_admin(client: TestClient) -> None:
    response = client.post("/api/v1/plates/read-manual", json={"plate": "ABC1D23"})

    assert response.status_code == 401


def test_manual_plate_read_with_inactive_vehicle_is_not_resolved(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers)

    vehicle_response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student["id"],
            "plate": "qwe-1a23",
            "brand": "Volkswagen",
            "model": "Gol",
            "color": "Prata",
            "is_active": False,
        },
        headers=headers,
    )
    assert vehicle_response.status_code == 201

    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "qwe-1a23"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "VEICULO_NAO_CADASTRADO"
    assert body["operational_decision"] == "VEICULO_NAO_CADASTRADO"
    assert body["vehicle"] is None
    assert body["person"] is None


def test_manual_plate_read_rejects_invalid_plate(
    client: TestClient, db_session: Session
) -> None:
    headers = _admin_headers(client)

    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "ABC"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_plate"
    assert response.json()["error"]["details"]["operational_decision"] == "PLACA_INVALIDA"
    details = response.json()["error"]["details"]
    event = db_session.get(AccessEvent, details["access_event_id"])
    plate_read = db_session.get(PlateRead, details["plate_read_id"])
    assert event is not None and event.status == "PLACA_INVALIDA"
    assert plate_read is not None and event.plate_read_id == plate_read.id
