from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.access_point import AccessPoint


def list_access_points(
    db: Session, *, is_active: bool | None = None, direction: str | None = None,
    name: str | None = None, skip: int = 0, limit: int = 100,
) -> list[AccessPoint]:
    statement = select(AccessPoint)
    if is_active is not None:
        statement = statement.where(AccessPoint.is_active.is_(is_active))
    if direction is not None:
        statement = statement.where(AccessPoint.direction == direction)
    if name is not None:
        statement = statement.where(
            func.lower(AccessPoint.name).contains(name.strip().lower())
        )
    statement = statement.order_by(AccessPoint.name, AccessPoint.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_access_point(db: Session, access_point_id: int) -> AccessPoint | None:
    return db.get(AccessPoint, access_point_id)


def create_access_point(db: Session, data: dict[str, object]) -> AccessPoint:
    access_point = AccessPoint(**data)
    db.add(access_point)
    return access_point


def update_access_point(
    access_point: AccessPoint, data: dict[str, object]
) -> AccessPoint:
    for field, value in data.items():
        setattr(access_point, field, value)
    return access_point


def deactivate_access_point(access_point: AccessPoint) -> AccessPoint:
    access_point.is_active = False
    return access_point
