import re

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.access_event import AccessEvent
from app.repositories import access_events as access_event_repository
from app.repositories import vehicles as vehicle_repository
from app.schemas.plate import ManualPlateReadRequest


_PLATE_CLEANER = re.compile(r"[^A-Za-z0-9]")


def normalize_plate(plate: str) -> str:
    return _PLATE_CLEANER.sub("", plate).upper()


def normalize_and_validate_plate(plate: str) -> str:
    normalized_plate = normalize_plate(plate)
    if len(normalized_plate) != 7 or not normalized_plate.isalnum():
        raise AppException(
            "Plate must have 7 alphanumeric characters.",
            status_code=400,
            code="invalid_plate",
        )
    return normalized_plate


def read_manual_plate(db: Session, payload: ManualPlateReadRequest) -> AccessEvent:
    plate_input = payload.plate
    plate_normalized = normalize_and_validate_plate(plate_input)
    vehicle = vehicle_repository.get_vehicle_by_plate(db, plate_normalized)

    event_data: dict[str, object] = {
        "plate_input": plate_input,
        "plate_normalized": plate_normalized,
        "source": "manual",
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

    access_event = access_event_repository.create_access_event(db, event_data)
    db.commit()
    db.refresh(access_event)
    return access_event
