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
from app.repositories import plate_reads as plate_read_repository
from app.schemas.plate import ManualPlateReadRequest, OperationalDecision
from app.services import access_events as access_event_service
from app.services import cameras as camera_service
from app.services.plate_utils import normalize_and_validate_plate, normalize_plate


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


def operational_decision_for_access_event(access_event: AccessEvent) -> OperationalDecision:
    if access_event.status in {
        "ACESSO_LIBERADO",
        "VEICULO_NAO_CADASTRADO",
        "PESSOA_NAO_VINCULADA",
        "OCR_BAIXA_CONFIANCA",
        "PLACA_INVALIDA",
        "ERRO_OCR",
        "CADASTRO_INATIVO",
    }:
        return access_event.status
    if access_event.vehicle is None:
        return "VEICULO_NAO_CADASTRADO"
    if access_event.person is None:
        return "PESSOA_NAO_VINCULADA"
    return "ACESSO_LIBERADO"


def operational_message(decision: OperationalDecision) -> str:
    return {
        "ACESSO_LIBERADO": "Acesso liberado.",
        "VEICULO_NAO_CADASTRADO": "Veiculo nao cadastrado.",
        "PESSOA_NAO_VINCULADA": "Veiculo sem pessoa ativa vinculada.",
        "OCR_BAIXA_CONFIANCA": "Leitura OCR com baixa confianca.",
        "PLACA_INVALIDA": "Placa invalida.",
        "ERRO_OCR": "Nao foi possivel realizar a leitura OCR.",
        "CADASTRO_INATIVO": "Veiculo ou pessoa com cadastro inativo.",
    }[decision]


def access_event_action(access_event: AccessEvent) -> str | None:
    if access_event.action is None:
        return None
    return access_event.action.code or access_event.action.name


def access_event_origin(access_event: AccessEvent) -> str | None:
    if access_event.origin_domain is None:
        return access_event.origin
    return access_event.origin_domain.code or access_event.origin_domain.name


def _error_operational_details(
    access_event: AccessEvent,
    *,
    decision: OperationalDecision,
    confidence: float | None = None,
) -> dict[str, object]:
    return {
        "operational_decision": decision,
        "message": operational_message(decision),
        "plate_input": access_event.plate_input,
        "plate_normalized": access_event.plate_normalized,
        "source": access_event.source,
        "confidence": confidence,
        "access_event_id": access_event.id,
        "plate_read_id": access_event.plate_read_id,
        "access_event": {
            "id": access_event.id,
            "plate_read_id": access_event.plate_read_id,
            "status": access_event.status,
            "plate_input": access_event.plate_input,
            "plate_normalized": access_event.plate_normalized,
            "source": access_event.source,
            "created_at": access_event.created_at.isoformat(),
        },
        "vehicle": None,
        "person": None,
        "person_type": None,
        "action": access_event_action(access_event),
        "origin": access_event_origin(access_event),
        "created_at": access_event.created_at.isoformat(),
        "vehicle_side": (
            access_event.plate_read.vehicle_side
            if access_event.plate_read is not None
            else "INDEFINIDO"
        ),
        "camera": (
            {"id": access_event.plate_read.camera.id, "name": access_event.plate_read.camera.name}
            if access_event.plate_read is not None
            and access_event.plate_read.camera is not None
            else None
        ),
        "access_point": (
            {
                "id": access_event.access_point.id,
                "name": access_event.access_point.name,
                "direction": access_event.access_point.direction,
            }
            if access_event.access_point is not None
            else None
        ),
    }


def _ocr_error_details(details: object | None) -> dict[str, object]:
    if isinstance(details, dict):
        return {**details, "operational_decision": OPERATIONAL_DECISION_OCR_ERROR}
    return {"operational_decision": OPERATIONAL_DECISION_OCR_ERROR}


def _register_plate_read_and_event(
    db: Session,
    *,
    plate_input: str,
    plate_normalized: str,
    source: str,
    confidence: float | None = None,
    image_path: str | None = None,
    status_override: OperationalDecision | None = None,
    camera_id: int | None = None,
    access_point_id: int | None = None,
    access_point_direction: str | None = None,
    vehicle_side: str = "INDEFINIDO",
) -> AccessEvent:
    plate_read = plate_read_repository.create_plate_read(
        db,
        {
            "vehicle_id": None,
            "camera_id": camera_id,
            "plate": plate_normalized[:10],
            "source": source,
            "confidence": _confidence_for_storage(confidence),
            "image_path": image_path,
            "vehicle_side": vehicle_side,
            "read_at": datetime.now(UTC).replace(tzinfo=None),
        },
    )
    db.flush()
    access_event = access_event_service.create_access_event_from_plate_read(
        db,
        plate_input=plate_input,
        plate_normalized=plate_normalized,
        origin=source,
        plate_read_id=plate_read.id,
        access_point_id=access_point_id,
        access_point_direction=access_point_direction,
        status_override=status_override,
    )
    plate_read.vehicle_id = access_event.vehicle_id
    return access_event


def read_manual_plate(db: Session, payload: ManualPlateReadRequest) -> AccessEvent:
    location = camera_service.resolve_read_location(
        db, camera_id=payload.camera_id, access_point_id=payload.access_point_id
    )
    plate_input = payload.plate
    plate_normalized = normalize_plate(plate_input)
    try:
        normalize_and_validate_plate(plate_input)
    except AppException as exc:
        access_event = _register_plate_read_and_event(
            db,
            plate_input=plate_input,
            plate_normalized=plate_normalized,
            source="manual",
            status_override=OPERATIONAL_DECISION_INVALID_PLATE,
            camera_id=location.camera.id if location.camera is not None else None,
            access_point_id=(
                location.access_point.id if location.access_point is not None else None
            ),
            access_point_direction=(
                location.access_point.direction
                if location.access_point is not None
                else None
            ),
            vehicle_side=payload.vehicle_side,
        )
        db.commit()
        raise AppException(
            exc.message,
            status_code=exc.status_code,
            code=exc.code,
            details={
                **(exc.details if isinstance(exc.details, dict) else {}),
                **_error_operational_details(
                    access_event, decision=OPERATIONAL_DECISION_INVALID_PLATE
                ),
            },
        ) from exc
    access_event = _register_plate_read_and_event(
        db,
        plate_input=plate_input,
        plate_normalized=plate_normalized,
        source="manual",
        camera_id=location.camera.id if location.camera is not None else None,
        access_point_id=(
            location.access_point.id if location.access_point is not None else None
        ),
        access_point_direction=(
            location.access_point.direction if location.access_point is not None else None
        ),
        vehicle_side=payload.vehicle_side,
    )
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


def read_image_plate(
    db: Session,
    file: UploadFile,
    mock_plate: str | None = None,
    *,
    camera_id: int | None = None,
    access_point_id: int | None = None,
    vehicle_side: str = "INDEFINIDO",
) -> ImagePlateReadResult:
    location = camera_service.resolve_read_location(
        db, camera_id=camera_id, access_point_id=access_point_id
    )
    image_path = _save_upload_file(file)
    confidence: float | None = None
    confidence_is_sufficient = True
    if mock_plate and mock_plate.strip():
        plate_input = mock_plate.strip()
    else:
        try:
            ocr_result = extract_plate_from_image(image_path)
        except AppException as exc:
            access_event = _register_plate_read_and_event(
                db,
                plate_input="",
                plate_normalized="",
                source="upload",
                image_path=image_path,
                status_override=OPERATIONAL_DECISION_OCR_ERROR,
                camera_id=location.camera.id if location.camera is not None else None,
                access_point_id=(
                    location.access_point.id if location.access_point is not None else None
                ),
                access_point_direction=(
                    location.access_point.direction
                    if location.access_point is not None
                    else None
                ),
                vehicle_side=vehicle_side,
            )
            db.commit()
            raise AppException(
                exc.message,
                status_code=exc.status_code,
                code=exc.code,
                details={
                    **_ocr_error_details(exc.details),
                    **_error_operational_details(
                        access_event, decision=OPERATIONAL_DECISION_OCR_ERROR
                    ),
                },
            ) from exc
        plate_input = ocr_result.plate_text
        confidence = ocr_result.confidence
        confidence_is_sufficient = _is_ocr_confidence_sufficient(confidence)

    plate_normalized = normalize_plate(plate_input)
    try:
        normalize_and_validate_plate(plate_input)
    except AppException as exc:
        access_event = _register_plate_read_and_event(
            db,
            plate_input=plate_input,
            plate_normalized=plate_normalized,
            source="upload",
            confidence=confidence,
            image_path=image_path,
            status_override=OPERATIONAL_DECISION_INVALID_PLATE,
            camera_id=location.camera.id if location.camera is not None else None,
            access_point_id=(
                location.access_point.id if location.access_point is not None else None
            ),
            access_point_direction=(
                location.access_point.direction
                if location.access_point is not None
                else None
            ),
            vehicle_side=vehicle_side,
        )
        db.commit()
        raise AppException(
            exc.message,
            status_code=exc.status_code,
            code=exc.code,
            details={
                **(exc.details if isinstance(exc.details, dict) else {}),
                **_error_operational_details(
                    access_event,
                    decision=OPERATIONAL_DECISION_INVALID_PLATE,
                    confidence=confidence,
                ),
            },
        ) from exc

    access_event = _register_plate_read_and_event(
        db,
        plate_input=plate_input,
        plate_normalized=plate_normalized,
        source="upload",
        confidence=confidence,
        image_path=image_path,
        status_override=None if confidence_is_sufficient else OPERATIONAL_DECISION_LOW_CONFIDENCE,
        camera_id=location.camera.id if location.camera is not None else None,
        access_point_id=(
            location.access_point.id if location.access_point is not None else None
        ),
        access_point_direction=(
            location.access_point.direction if location.access_point is not None else None
        ),
        vehicle_side=vehicle_side,
    )
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
