from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.vehicle import Vehicle
from app.repositories import vehicles as vehicle_repository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.plates import normalize_and_validate_plate
from app.services.students import get_active_student_or_404


def list_vehicles(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    student_id: int | None = None,
) -> list[Vehicle]:
    return vehicle_repository.list_vehicles(db, skip=skip, limit=limit, student_id=student_id)


def get_vehicle_or_404(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = vehicle_repository.get_vehicle(db, vehicle_id)
    if vehicle is None:
        raise AppException(
            "Vehicle was not found.",
            status_code=404,
            code="vehicle_not_found",
        )
    return vehicle


def get_vehicle_by_plate_or_404(db: Session, plate: str) -> Vehicle:
    normalized_plate = normalize_and_validate_plate(plate)
    vehicle = vehicle_repository.get_vehicle_by_plate(db, normalized_plate)
    if vehicle is None:
        raise AppException(
            "Vehicle was not found.",
            status_code=404,
            code="vehicle_not_found",
        )
    return vehicle


def _ensure_unique_plate(
    db: Session,
    plate: str,
    *,
    current_vehicle_id: int | None = None,
) -> None:
    vehicle = vehicle_repository.get_active_vehicle_by_plate(db, plate)
    if vehicle is not None and vehicle.id != current_vehicle_id:
        raise AppException(
            "Vehicle plate already exists.",
            status_code=409,
            code="vehicle_plate_conflict",
        )


def create_vehicle(db: Session, payload: VehicleCreate) -> Vehicle:
    data = payload.model_dump()
    get_active_student_or_404(db, int(data["student_id"]))
    data["plate"] = normalize_and_validate_plate(str(data["plate"]))
    _ensure_unique_plate(db, str(data["plate"]))

    vehicle = vehicle_repository.create_vehicle(db, data)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Vehicle unique data already exists.",
            status_code=409,
            code="vehicle_plate_conflict",
        ) from None
    db.refresh(vehicle)
    return vehicle


def update_vehicle(db: Session, vehicle_id: int, payload: VehicleUpdate) -> Vehicle:
    vehicle = get_vehicle_or_404(db, vehicle_id)
    data = payload.model_dump(exclude_unset=True)

    if "student_id" in data:
        get_active_student_or_404(db, int(data["student_id"]))

    if "plate" in data:
        data["plate"] = normalize_and_validate_plate(str(data["plate"]))
        _ensure_unique_plate(db, str(data["plate"]), current_vehicle_id=vehicle.id)

    vehicle_repository.update_vehicle(vehicle, data)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Vehicle unique data already exists.",
            status_code=409,
            code="vehicle_plate_conflict",
        ) from None
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: int) -> None:
    vehicle = get_vehicle_or_404(db, vehicle_id)
    vehicle_repository.deactivate_vehicle(vehicle)
    db.commit()
