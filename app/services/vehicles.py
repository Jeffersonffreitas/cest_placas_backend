from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.vehicle import Vehicle
from app.models.domain import Domain
from app.repositories import vehicles as vehicle_repository
from app.repositories import domains as domain_repository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.plates import normalize_and_validate_plate
from app.services.students import get_active_student_or_404


VEHICLE_DOMAIN_FIELDS = {
    "brand": ("brand_id", "MARCA_VEICULO"),
    "model": ("model_id", "MODELO_VEICULO"),
    "color": ("color_id", "COR_VEICULO"),
}


def _active_domain(db: Session, domain_id: int, expected_type: str, field: str) -> Domain:
    domain = domain_repository.get_domain(db, domain_id)
    if domain is None or not domain.is_active or domain.type != expected_type:
        raise AppException(
            f"{field} must reference an active {expected_type} domain.",
            status_code=422,
            code=f"invalid_{field}",
        )
    return domain


def _domain_for_text(db: Session, value: str, expected_type: str) -> Domain | None:
    name = value.strip()
    if not name:
        return None
    domain = domain_repository.get_by_type_and_name(db, type=expected_type, name=name)
    if domain is None:
        domain = domain_repository.create_domain(
            db,
            {"type": expected_type, "code": None, "name": name, "is_active": True},
        )
        db.flush()
    elif not domain.is_active:
        domain.is_active = True
    return domain


def _resolve_vehicle_domains(db: Session, data: dict[str, object]) -> None:
    for text_field, (id_field, expected_type) in VEHICLE_DOMAIN_FIELDS.items():
        if id_field in data and data[id_field] is not None:
            domain = _active_domain(db, int(data[id_field]), expected_type, id_field)
            data[text_field] = domain.name
        elif text_field in data:
            text_value = data[text_field]
            if text_value is None or not str(text_value).strip():
                data[text_field] = None
                data[id_field] = None
            else:
                domain = _domain_for_text(db, str(text_value), expected_type)
                data[text_field] = str(text_value).strip()
                data[id_field] = domain.id if domain is not None else None


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
    _resolve_vehicle_domains(db, data)

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

    _resolve_vehicle_domains(db, data)

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
