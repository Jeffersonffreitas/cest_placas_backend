from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.vehicle import Vehicle


def list_vehicles(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    student_id: int | None = None,
) -> list[Vehicle]:
    statement = select(Vehicle).options(
        selectinload(Vehicle.brand_domain),
        selectinload(Vehicle.model_domain),
        selectinload(Vehicle.color_domain),
    )
    if student_id is not None:
        statement = statement.where(Vehicle.student_id == student_id)
    statement = statement.order_by(Vehicle.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle | None:
    statement = select(Vehicle).where(Vehicle.id == vehicle_id).options(
        selectinload(Vehicle.brand_domain),
        selectinload(Vehicle.model_domain),
        selectinload(Vehicle.color_domain),
    )
    return db.scalars(statement).first()


def get_vehicle_by_plate(db: Session, plate: str) -> Vehicle | None:
    statement = select(Vehicle).where(Vehicle.plate == plate).options(
        selectinload(Vehicle.brand_domain),
        selectinload(Vehicle.model_domain),
        selectinload(Vehicle.color_domain),
    )
    return db.scalars(statement).first()


def get_active_vehicle_by_plate(db: Session, plate: str) -> Vehicle | None:
    statement = select(Vehicle).where(
        Vehicle.plate == plate,
        Vehicle.is_active.is_(True),
    )
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
