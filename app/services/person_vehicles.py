from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.vehicle import Vehicle
from app.repositories import people as person_repository
from app.repositories import person_vehicles as link_repository
from app.repositories import vehicles as vehicle_repository
from app.schemas.person_vehicle import PersonVehicleCreate


def list_person_vehicles(
    db: Session, *, person_id: int | None = None, vehicle_id: int | None = None,
    is_active: bool | None = None, skip: int = 0, limit: int = 100,
) -> list[PersonVehicle]:
    return link_repository.list_person_vehicles(
        db, person_id=person_id, vehicle_id=vehicle_id, is_active=is_active,
        skip=skip, limit=limit,
    )


def get_person_vehicle_or_404(db: Session, person_vehicle_id: int) -> PersonVehicle:
    link = link_repository.get_person_vehicle(db, person_vehicle_id)
    if link is None:
        raise AppException(
            "Person-vehicle link was not found.",
            status_code=404,
            code="person_vehicle_not_found",
        )
    return link


def _get_active_person(db: Session, person_id: int) -> Person:
    person = person_repository.get_person(db, person_id)
    if person is None:
        raise AppException("Person was not found.", status_code=404, code="person_not_found")
    if not person.is_active:
        raise AppException("Person is inactive.", status_code=409, code="person_inactive")
    return person


def _get_active_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = vehicle_repository.get_vehicle(db, vehicle_id)
    if vehicle is None:
        raise AppException("Vehicle was not found.", status_code=404, code="vehicle_not_found")
    if not vehicle.is_active:
        raise AppException("Vehicle is inactive.", status_code=409, code="vehicle_inactive")
    return vehicle


def _commit(db: Session, link: PersonVehicle) -> PersonVehicle:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "An active link between this person and vehicle already exists.",
            status_code=409,
            code="person_vehicle_conflict",
        ) from None
    db.refresh(link)
    return link


def create_person_vehicle(
    db: Session, payload: PersonVehicleCreate,
) -> PersonVehicle:
    _get_active_person(db, payload.person_id)
    _get_active_vehicle(db, payload.vehicle_id)
    existing = link_repository.get_by_pair(
        db, person_id=payload.person_id, vehicle_id=payload.vehicle_id
    )
    if existing is not None:
        if existing.is_active:
            raise AppException(
                "An active link between this person and vehicle already exists.",
                status_code=409,
                code="person_vehicle_conflict",
            )
        existing.is_active = True
        return _commit(db, existing)
    link = link_repository.create_person_vehicle(db, payload.model_dump())
    return _commit(db, link)


def delete_person_vehicle(db: Session, person_vehicle_id: int) -> None:
    link = get_person_vehicle_or_404(db, person_vehicle_id)
    link_repository.deactivate_person_vehicle(link)
    db.commit()


def list_vehicles_for_person(
    db: Session, person_id: int, *, skip: int = 0, limit: int = 100,
) -> list[Vehicle]:
    if person_repository.get_person(db, person_id) is None:
        raise AppException("Person was not found.", status_code=404, code="person_not_found")
    return link_repository.list_vehicles_for_person(
        db, person_id, skip=skip, limit=limit
    )


def list_people_for_vehicle(
    db: Session, vehicle_id: int, *, skip: int = 0, limit: int = 100,
) -> list[Person]:
    if vehicle_repository.get_vehicle(db, vehicle_id) is None:
        raise AppException("Vehicle was not found.", status_code=404, code="vehicle_not_found")
    return link_repository.list_people_for_vehicle(
        db, vehicle_id, skip=skip, limit=limit
    )
