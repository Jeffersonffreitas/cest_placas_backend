from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.ocr import OCRPlateResult, extract_plate_candidate
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
    monkeypatch: pytest.MonkeyPatch,
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

    def fail_if_ocr_is_called(image_path: str) -> OCRPlateResult:
        raise AssertionError(f"OCR should not be called when mock_plate is provided: {image_path}")

    monkeypatch.setattr(plate_service, "extract_plate_from_image", fail_if_ocr_is_called)

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
    assert body["confidence"] is None
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
    assert plate_read.confidence is None


def test_image_plate_read_uses_ocr_when_mock_plate_is_missing_and_registers_not_found(
    client: TestClient,
    db_session: Session,
    upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _admin_headers(client)

    def fake_extract_plate_from_image(image_path: str) -> OCRPlateResult:
        assert image_path.startswith(upload_dir.as_posix())
        assert Path(image_path).read_bytes() == b"other-image"
        return OCRPlateResult(plate_text="ZZZ9Z99", confidence=87.54, raw_text="ZZZ9Z99")

    monkeypatch.setattr(plate_service, "extract_plate_from_image", fake_extract_plate_from_image)

    response = client.post(
        "/api/v1/plates/read-image",
        files={"file": ("entrada-sem-placa-no-nome.png", b"other-image", "image/png")},
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
    assert body["confidence"] == 87.54
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
    assert float(plate_read.confidence) == 87.54


def test_extract_plate_candidate_accepts_brazilian_patterns_and_common_ocr_noise() -> None:
    assert extract_plate_candidate(["entrada ", "abc1d23"]) == "ABC1D23"
    assert extract_plate_candidate(["placa ABClD23"]) == "ABC1D23"


@pytest.mark.parametrize(
    ("ocr_texts", "expected_plate"),
    [
        (["placa AB01D23"], "ABO1D23"),
        (["placa A8C1D23"], "ABC1D23"),
        (["placa ABCID23"], "ABC1D23"),
        (["placa ABC1D2O"], "ABC1D20"),
        (["placa ABC1D2S"], "ABC1D25"),
        (["placa ABC1DZ3"], "ABC1D23"),
    ],
)
def test_extract_plate_candidate_corrects_common_ocr_confusions(
    ocr_texts: list[str],
    expected_plate: str,
) -> None:
    assert extract_plate_candidate(ocr_texts) == expected_plate


def test_extract_plate_candidate_accepts_old_brazilian_plate_pattern() -> None:
    assert extract_plate_candidate(["entrada ABC1234"]) == "ABC1234"
