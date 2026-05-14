from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.access_event import AccessEvent


def list_access_events(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    plate_normalized: str | None = None,
    status: str | None = None,
    student_id: int | None = None,
    vehicle_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AccessEvent]:
    statement = select(AccessEvent).options(
        joinedload(AccessEvent.student),
        joinedload(AccessEvent.vehicle),
    )
    if plate_normalized is not None:
        statement = statement.where(AccessEvent.plate_normalized == plate_normalized)
    if status is not None:
        statement = statement.where(AccessEvent.status == status)
    if student_id is not None:
        statement = statement.where(AccessEvent.student_id == student_id)
    if vehicle_id is not None:
        statement = statement.where(AccessEvent.vehicle_id == vehicle_id)
    if date_from is not None:
        statement = statement.where(AccessEvent.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(AccessEvent.created_at <= date_to)

    statement = (
        statement.order_by(AccessEvent.created_at.desc(), AccessEvent.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def create_access_event(db: Session, data: dict[str, object]) -> AccessEvent:
    access_event = AccessEvent(**data)
    db.add(access_event)
    return access_event
