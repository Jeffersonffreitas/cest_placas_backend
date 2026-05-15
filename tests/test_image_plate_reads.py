from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.plate_read import PlateRead
from app.services import plates as plate_service


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
            "registration_number": "20260003",
            "full_name": "Ana Costa",
            "email": "ana.costa@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "plate_reads"
    monkeypatch.setattr(plate_service, "PLATE_READ_UPLOAD_DIR", directory)
    return directory


def test_image_plate_read_with_mock_plate_matches_vehicle_and_registers_records(
    client: TestClient,
    db_session: Session,
    upload_dir: Path,
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
        "/api/v1/plates/read-image",
        data={"mock_plate": " abc-1d23 "},
        files={"file": ("foto-sem-placa.jpg", b"fake-image", "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["plate_input"] == "abc-1d23"
    assert body["plate_normalized"] == "ABC1D23"
    assert body["source"] == "upload"
    assert body["status"] == "matched"
    assert body["vehicle"]["id"] == vehicle["id"]
    assert body["student"]["id"] == student["id"]
    assert body["image_path"].startswith(upload_dir.as_posix())
    assert Path(body["image_path"]).read_bytes() == b"fake-image"

    access_event = db_session.scalars(select(AccessEvent)).one()
    assert access_event.plate_input == "abc-1d23"
    assert access_event.plate_normalized == "ABC1D23"
    assert access_event.source == "upload"
    assert access_event.status == "matched"
    assert access_event.vehicle_id == vehicle["id"]
    assert access_event.student_id == student["id"]

    plate_read = db_session.scalars(select(PlateRead)).one()
    assert plate_read.plate == "ABC1D23"
    assert plate_read.source == "upload"
    assert plate_read.vehicle_id == vehicle["id"]
    assert plate_read.image_path == body["image_path"]


def test_image_plate_read_infers_plate_from_filename_and_registers_not_found(
    client: TestClient,
    db_session: Session,
    upload_dir: Path,
) -> None:
    headers = _admin_headers(client)

    response = client.post(
        "/api/v1/plates/read-image",
        files={"file": ("entrada_zzz-9z99.png", b"other-image", "image/png")},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["plate_input"] == "ZZZ9Z99"
    assert body["plate_normalized"] == "ZZZ9Z99"
    assert body["source"] == "upload"
    assert body["status"] == "not_found"
    assert body["vehicle"] is None
    assert body["student"] is None
    assert body["image_path"].startswith(upload_dir.as_posix())
    assert Path(body["image_path"]).read_bytes() == b"other-image"

    access_event = db_session.scalars(select(AccessEvent)).one()
    assert access_event.plate_input == "ZZZ9Z99"
    assert access_event.plate_normalized == "ZZZ9Z99"
    assert access_event.source == "upload"
    assert access_event.status == "not_found"
    assert access_event.vehicle_id is None
    assert access_event.student_id is None

    plate_read = db_session.scalars(select(PlateRead)).one()
    assert plate_read.plate == "ZZZ9Z99"
    assert plate_read.source == "upload"
    assert plate_read.vehicle_id is None
    assert plate_read.image_path == body["image_path"]
