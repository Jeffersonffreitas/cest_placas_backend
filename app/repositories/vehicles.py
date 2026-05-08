from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle


def list_vehicles(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    student_id: int | None = None,
) -> list[Vehicle]:
    statement = select(Vehicle)
    if student_id is not None:
        statement = statement.where(Vehicle.student_id == student_id)
    statement = statement.order_by(Vehicle.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle | None:
    return db.get(Vehicle, vehicle_id)


def get_vehicle_by_plate(db: Session, plate: str) -> Vehicle | None:
    statement = select(Vehicle).where(Vehicle.plate == plate)
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
