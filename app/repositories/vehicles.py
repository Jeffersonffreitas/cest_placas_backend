from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.vehicle import Vehicle


def _vehicle_load_options():
    return (
        selectinload(Vehicle.brand_domain),
        selectinload(Vehicle.model_domain),
        selectinload(Vehicle.color_domain),
        selectinload(Vehicle.person_links).selectinload(PersonVehicle.person),
    )


def list_vehicles(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    student_id: int | None = None,
) -> list[Vehicle]:
    statement = select(Vehicle).options(*_vehicle_load_options())
    if student_id is not None:
        statement = (
            statement.join(PersonVehicle, PersonVehicle.vehicle_id == Vehicle.id)
            .join(Person, Person.id == PersonVehicle.person_id)
            .where(
                PersonVehicle.person_id == student_id,
                PersonVehicle.is_active.is_(True),
                Person.person_type == "ALUNO",
            )
        )
    statement = statement.order_by(Vehicle.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle | None:
    statement = select(Vehicle).where(Vehicle.id == vehicle_id).options(
        *_vehicle_load_options()
    )
    return db.scalars(statement).first()


def get_vehicle_by_plate(db: Session, plate: str) -> Vehicle | None:
    statement = select(Vehicle).where(Vehicle.plate == plate).options(
        *_vehicle_load_options()
    )
    return db.scalars(statement).first()


def get_active_vehicle_by_plate(db: Session, plate: str) -> Vehicle | None:
    statement = select(Vehicle).where(
        Vehicle.plate == plate,
        Vehicle.is_active.is_(True),
    ).options(*_vehicle_load_options())
    return db.scalars(statement).first()


def create_vehicle(db: Session, data: dict[str, object]) -> Vehicle:
    vehicle = Vehicle(**data)
    db.add(vehicle)
    return vehicle


def update_vehicle(vehicle: Vehicle, data: dict[str, object]) -> Vehicle:
    for field, value in data.items():
        setattr(vehicle, field, value)
    return vehicle


def delete_vehicle(db: Session, vehicle: Vehicle) -> None:
    db.delete(vehicle)


def deactivate_vehicle(vehicle: Vehicle) -> Vehicle:
    vehicle.is_active = False
    return vehicle
