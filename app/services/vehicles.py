from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.vehicle import Vehicle
from app.models.domain import Domain
from app.repositories import people as person_repository
from app.repositories import person_vehicles as link_repository
from app.repositories import students as student_repository
from app.repositories import vehicles as vehicle_repository
from app.repositories import domains as domain_repository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.plates import normalize_and_validate_plate


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


def _active_person_or_404(db: Session, person_id: int) -> Person:
    person = person_repository.get_person(db, person_id)
    if person is None:
        raise AppException(
            "Person was not found.", status_code=404, code="person_not_found"
        )
    if not person.is_active:
        raise AppException(
            "Person is inactive.", status_code=409, code="person_inactive"
        )
    return person


def _active_student_person_or_404(db: Session, student_id: int) -> Person:
    student = student_repository.get_student(db, student_id)
    if student is None:
        raise AppException(
            "Student was not found.", status_code=404, code="student_not_found"
        )
    if not student.is_active:
        raise AppException(
            "Student is inactive.", status_code=409, code="student_inactive"
        )
    return student


def _requested_people(db: Session, data: dict[str, object]) -> list[Person]:
    people: list[Person] = []
    person_id = data.pop("person_id", None)
    student_id = data.pop("student_id", None)
    if person_id is not None:
        people.append(_active_person_or_404(db, int(person_id)))
    if student_id is not None:
        student = _active_student_person_or_404(db, int(student_id))
        if all(person.id != student.id for person in people):
            people.append(student)
    return people


def _add_links(
    db: Session, vehicle: Vehicle, people: list[Person], *, reject_existing: bool,
) -> None:
    for person in people:
        existing = link_repository.get_by_pair(
            db, person_id=person.id, vehicle_id=vehicle.id
        )
        if existing is not None:
            if existing.is_active and reject_existing:
                raise AppException(
                    "An active link between this person and vehicle already exists.",
                    status_code=409,
                    code="person_vehicle_conflict",
                )
            existing.is_active = True
            continue
        link = PersonVehicle(person=person, vehicle=vehicle, is_active=True)
        db.add(link)


def _ensure_linkable_vehicle(is_active: bool, has_requested_people: bool) -> None:
    if has_requested_people and not is_active:
        raise AppException(
            "Vehicle is inactive.", status_code=409, code="vehicle_inactive"
        )


def create_vehicle(db: Session, payload: VehicleCreate) -> Vehicle:
    data = payload.model_dump()
    people = _requested_people(db, data)
    data["plate"] = normalize_and_validate_plate(str(data["plate"]))
    _ensure_unique_plate(db, str(data["plate"]))
    _ensure_linkable_vehicle(
        bool(data.get("is_active", True)), payload.person_id is not None
    )
    _resolve_vehicle_domains(db, data)

    vehicle = vehicle_repository.create_vehicle(db, data)
    try:
        db.flush()
        _add_links(db, vehicle, people, reject_existing=False)
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
    people = _requested_people(db, data)

    if "plate" in data:
        data["plate"] = normalize_and_validate_plate(str(data["plate"]))
        _ensure_unique_plate(db, str(data["plate"]), current_vehicle_id=vehicle.id)

    _ensure_linkable_vehicle(
        bool(data.get("is_active", vehicle.is_active)), payload.person_id is not None
    )
    _resolve_vehicle_domains(db, data)

    vehicle_repository.update_vehicle(vehicle, data)
    try:
        _add_links(db, vehicle, people, reject_existing=True)
        db.commit()
    except AppException:
        db.rollback()
        raise
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
