from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.vehicle import Vehicle


def list_person_vehicles(
    db: Session, *, person_id: int | None = None, vehicle_id: int | None = None,
    is_active: bool | None = None, skip: int = 0, limit: int = 100,
) -> list[PersonVehicle]:
    statement = select(PersonVehicle)
    if person_id is not None:
        statement = statement.where(PersonVehicle.person_id == person_id)
    if vehicle_id is not None:
        statement = statement.where(PersonVehicle.vehicle_id == vehicle_id)
    if is_active is not None:
        statement = statement.where(PersonVehicle.is_active.is_(is_active))
    statement = statement.order_by(PersonVehicle.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_person_vehicle(db: Session, person_vehicle_id: int) -> PersonVehicle | None:
    return db.get(PersonVehicle, person_vehicle_id)


def get_by_pair(
    db: Session, *, person_id: int, vehicle_id: int,
) -> PersonVehicle | None:
    statement = select(PersonVehicle).where(
        PersonVehicle.person_id == person_id,
        PersonVehicle.vehicle_id == vehicle_id,
    )
    return db.scalars(statement).first()


def create_person_vehicle(
    db: Session, data: dict[str, object],
) -> PersonVehicle:
    link = PersonVehicle(**data)
    db.add(link)
    return link


def deactivate_person_vehicle(link: PersonVehicle) -> PersonVehicle:
    link.is_active = False
    return link


def list_vehicles_for_person(
    db: Session, person_id: int, *, skip: int = 0, limit: int = 100,
) -> list[Vehicle]:
    statement = (
        select(Vehicle)
        .join(PersonVehicle, PersonVehicle.vehicle_id == Vehicle.id)
        .where(
            PersonVehicle.person_id == person_id,
            PersonVehicle.is_active.is_(True),
        )
        .order_by(Vehicle.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def list_people_for_vehicle(
    db: Session, vehicle_id: int, *, skip: int = 0, limit: int = 100,
) -> list[Person]:
    statement = (
        select(Person)
        .join(PersonVehicle, PersonVehicle.person_id == Person.id)
        .where(
            PersonVehicle.vehicle_id == vehicle_id,
            PersonVehicle.is_active.is_(True),
        )
        .order_by(Person.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())
