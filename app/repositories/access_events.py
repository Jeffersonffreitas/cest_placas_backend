from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.access_event import AccessEvent


ACCESS_EVENT_STATUSES = ("matched", "not_found")
ACCESS_EVENT_SOURCES = ("manual", "upload")


def _apply_access_event_filters(
    statement,
    *,
    plate_normalized: str | None = None,
    source: str | None = None,
    status: str | None = None,
    student_id: int | None = None,
    vehicle_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    if plate_normalized is not None:
        statement = statement.where(AccessEvent.plate_normalized == plate_normalized)
    if source is not None:
        statement = statement.where(AccessEvent.source == source)
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
    return statement


def list_access_events(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    plate_normalized: str | None = None,
    source: str | None = None,
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
    statement = _apply_access_event_filters(
        statement,
        plate_normalized=plate_normalized,
        source=source,
        status=status,
        student_id=student_id,
        vehicle_id=vehicle_id,
        date_from=date_from,
        date_to=date_to,
    )
    statement = (
        statement.order_by(AccessEvent.created_at.desc(), AccessEvent.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def summarize_access_events(
    db: Session,
    *,
    source: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, object]:
    total_statement = _apply_access_event_filters(
        select(func.count(AccessEvent.id)),
        source=source,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    total_events = int(db.scalar(total_statement) or 0)

    status_statement = _apply_access_event_filters(
        select(AccessEvent.status, func.count(AccessEvent.id)).group_by(AccessEvent.status),
        source=source,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    total_by_status = {status_key: 0 for status_key in ACCESS_EVENT_STATUSES}
    total_by_status.update(
        {row_status: int(total) for row_status, total in db.execute(status_statement).all()},
    )

    source_statement = _apply_access_event_filters(
        select(AccessEvent.source, func.count(AccessEvent.id)).group_by(AccessEvent.source),
        source=source,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    total_by_source = {source_key: 0 for source_key in ACCESS_EVENT_SOURCES}
    total_by_source.update(
        {row_source: int(total) for row_source, total in db.execute(source_statement).all()},
    )

    return {
        "total_events": total_events,
        "total_matched": total_by_status["matched"],
        "total_not_found": total_by_status["not_found"],
        "total_manual": total_by_source["manual"],
        "total_upload": total_by_source["upload"],
        "total_by_status": total_by_status,
        "total_by_source": total_by_source,
    }


def create_access_event(db: Session, data: dict[str, object]) -> AccessEvent:
    access_event = AccessEvent(**data)
    db.add(access_event)
    return access_event
