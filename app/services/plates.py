import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.integrations.ocr import extract_plate_from_image
from app.models.access_event import AccessEvent
from app.repositories import access_events as access_event_repository
from app.repositories import plate_reads as plate_read_repository
from app.repositories import vehicles as vehicle_repository
from app.schemas.plate import ManualPlateReadRequest, OperationalDecision


_PLATE_CLEANER = re.compile(r"[^A-Za-z0-9]")
PLATE_READ_UPLOAD_DIR = Path("uploads/plate_reads")
MIN_OCR_CONFIDENCE = 70.0
OPERATIONAL_DECISION_INVALID_PLATE: OperationalDecision = "PLACA_INVALIDA"
OPERATIONAL_DECISION_OCR_ERROR: OperationalDecision = "ERRO_OCR"
OPERATIONAL_DECISION_LOW_CONFIDENCE: OperationalDecision = "OCR_BAIXA_CONFIANCA"


@dataclass(frozen=True)
class ImagePlateReadResult:
    access_event: AccessEvent
    image_path: str
    confidence: float | None
    operational_decision: OperationalDecision


def normalize_plate(plate: str) -> str:
    return _PLATE_CLEANER.sub("", plate).upper()


def normalize_and_validate_plate(plate: str) -> str:
    normalized_plate = normalize_plate(plate)
    if len(normalized_plate) != 7 or not normalized_plate.isalnum():
        raise AppException(
            "Plate must have 7 alphanumeric characters.",
            status_code=400,
            code="invalid_plate",
            details={"operational_decision": OPERATIONAL_DECISION_INVALID_PLATE},
        )
    return normalized_plate


def operational_decision_for_access_event(access_event: AccessEvent) -> OperationalDecision:
    vehicle = access_event.vehicle
    student = access_event.student
    if vehicle is None or student is None:
        return "VEICULO_NAO_CADASTRADO"
    if vehicle.is_active and student.is_active:
        return "ACESSO_LIBERADO"
    return "CADASTRO_INATIVO"


def _ocr_error_details(details: object | None) -> dict[str, object]:
    if isinstance(details, dict):
        return {**details, "operational_decision": OPERATIONAL_DECISION_OCR_ERROR}
    return {"operational_decision": OPERATIONAL_DECISION_OCR_ERROR}


def _create_access_event_for_plate(db: Session, plate_input: str, plate_normalized: str, source: str) -> AccessEvent:
    vehicle = vehicle_repository.get_vehicle_by_plate(db, plate_normalized)

    event_data: dict[str, object] = {
        "plate_input": plate_input,
        "plate_normalized": plate_normalized,
        "source": source,
        "status": "not_found",
        "vehicle_id": None,
        "student_id": None,
    }
    if vehicle is not None:
        event_data.update(
            {
                "status": "matched",
                "vehicle_id": vehicle.id,
                "student_id": vehicle.student_id,
            },
        )

    return access_event_repository.create_access_event(db, event_data)


def _create_unmatched_access_event_for_plate(
    db: Session,
    plate_input: str,
    plate_normalized: str,
    source: str,
) -> AccessEvent:
    return access_event_repository.create_access_event(
        db,
        {
            "plate_input": plate_input,
            "plate_normalized": plate_normalized,
            "source": source,
            "status": "not_found",
            "vehicle_id": None,
            "student_id": None,
        },
    )


def read_manual_plate(db: Session, payload: ManualPlateReadRequest) -> AccessEvent:
    plate_input = payload.plate
    plate_normalized = normalize_and_validate_plate(plate_input)
    access_event = _create_access_event_for_plate(db, plate_input, plate_normalized, "manual")
    db.commit()
    db.refresh(access_event)
    return access_event


def _safe_upload_filename(filename: str) -> str:
    safe_name = Path(filename).name or "plate-image"
    return f"{uuid4().hex}_{safe_name}"


def _save_upload_file(file: UploadFile) -> str:
    PLATE_READ_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = PLATE_READ_UPLOAD_DIR / _safe_upload_filename(file.filename or "plate-image")
    with destination.open("wb") as output_file:
        shutil.copyfileobj(file.file, output_file)
    return destination.as_posix()


def _confidence_for_storage(confidence: float | None) -> Decimal | None:
    if confidence is None:
        return None
    return Decimal(str(confidence)).quantize(Decimal("0.01"))


def _is_ocr_confidence_sufficient(confidence: float | None) -> bool:
    return confidence is not None and confidence >= MIN_OCR_CONFIDENCE


def read_image_plate(db: Session, file: UploadFile, mock_plate: str | None = None) -> ImagePlateReadResult:
    image_path = _save_upload_file(file)
    confidence: float | None = None
    confidence_is_sufficient = True
    if mock_plate and mock_plate.strip():
        plate_input = mock_plate.strip()
    else:
        try:
            ocr_result = extract_plate_from_image(image_path)
        except AppException as exc:
            raise AppException(
                exc.message,
                status_code=exc.status_code,
                code=exc.code,
                details=_ocr_error_details(exc.details),
            ) from exc
        plate_input = ocr_result.plate_text
        confidence = ocr_result.confidence
        confidence_is_sufficient = _is_ocr_confidence_sufficient(confidence)

    plate_normalized = normalize_and_validate_plate(plate_input)
    vehicle = vehicle_repository.get_vehicle_by_plate(db, plate_normalized) if confidence_is_sufficient else None

    plate_read_repository.create_plate_read(
        db,
        {
            "vehicle_id": vehicle.id if vehicle is not None else None,
            "plate": plate_normalized,
            "source": "upload",
            "confidence": _confidence_for_storage(confidence),
            "image_path": image_path,
            "read_at": datetime.now(UTC).replace(tzinfo=None),
        },
    )
    if confidence_is_sufficient:
        access_event = _create_access_event_for_plate(db, plate_input, plate_normalized, "upload")
    else:
        access_event = _create_unmatched_access_event_for_plate(db, plate_input, plate_normalized, "upload")
    db.commit()
    db.refresh(access_event)
    operational_decision = (
        operational_decision_for_access_event(access_event)
        if confidence_is_sufficient
        else OPERATIONAL_DECISION_LOW_CONFIDENCE
    )
    return ImagePlateReadResult(
        access_event=access_event,
        image_path=image_path,
        confidence=confidence,
        operational_decision=operational_decision,
    )
