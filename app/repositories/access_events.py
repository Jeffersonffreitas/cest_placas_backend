from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.access_event import AccessEvent
from app.models.domain import Domain
from app.models.person import Person


def _apply_access_event_filters(
    statement,
    *,
    plate_normalized: str | None = None,
    origin: str | None = None,
    status: str | None = None,
    person_id: int | None = None,
    vehicle_id: int | None = None,
    action_id: int | None = None,
    origin_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    if plate_normalized is not None:
        statement = statement.where(AccessEvent.plate_normalized == plate_normalized)
    if origin is not None:
        statement = statement.where(AccessEvent.origin == origin)
    if status is not None:
        statement = statement.where(AccessEvent.status == status)
    if person_id is not None:
        statement = statement.where(AccessEvent.person_id == person_id)
    if vehicle_id is not None:
        statement = statement.where(AccessEvent.vehicle_id == vehicle_id)
    if action_id is not None:
        statement = statement.where(AccessEvent.action_id == action_id)
    if origin_id is not None:
        statement = statement.where(AccessEvent.origin_id == origin_id)
    if date_from is not None:
        statement = statement.where(AccessEvent.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(AccessEvent.created_at <= date_to)
    return statement


def _load_options():
    return (
        joinedload(AccessEvent.vehicle),
        joinedload(AccessEvent.person),
        joinedload(AccessEvent.plate_read),
        joinedload(AccessEvent.action),
        joinedload(AccessEvent.origin_domain),
    )


def list_access_events(db: Session, *, skip: int = 0, limit: int = 100, **filters) -> list[AccessEvent]:
    statement = _apply_access_event_filters(
        select(AccessEvent).options(*_load_options()), **filters
    )
    statement = statement.order_by(
        AccessEvent.created_at.desc(), AccessEvent.id.desc()
    ).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_access_event(db: Session, access_event_id: int) -> AccessEvent | None:
    statement = select(AccessEvent).where(AccessEvent.id == access_event_id).options(
        *_load_options()
    )
    return db.scalars(statement).first()


def _count_map(db: Session, statement) -> dict[str, int]:
    return {
        str(key) if key is not None else "NAO_INFORMADO": int(total)
        for key, total in db.execute(statement).all()
    }


def summarize_access_events(db: Session, **filters) -> dict[str, object]:
    total = int(db.scalar(_apply_access_event_filters(
        select(func.count(AccessEvent.id)), **filters
    )) or 0)
    by_status = _count_map(db, _apply_access_event_filters(
        select(AccessEvent.status, func.count(AccessEvent.id)).group_by(AccessEvent.status),
        **filters,
    ))
    origin_domain = aliased(Domain)
    origin_key = func.coalesce(
        origin_domain.code, origin_domain.name, AccessEvent.origin, "NAO_INFORMADO"
    )
    origin_statement = (
        select(origin_key, func.count(AccessEvent.id))
        .select_from(AccessEvent)
        .outerjoin(origin_domain, origin_domain.id == AccessEvent.origin_id)
        .group_by(
            origin_domain.code,
            origin_domain.name,
            AccessEvent.origin,
        )
    )
    by_origin = _count_map(
        db, _apply_access_event_filters(origin_statement, **filters)
    )

    action_domain = aliased(Domain)
    action_statement = (
        select(
            func.coalesce(action_domain.code, action_domain.name, "NAO_INFORMADO"),
            func.count(AccessEvent.id),
        )
        .select_from(AccessEvent)
        .outerjoin(action_domain, action_domain.id == AccessEvent.action_id)
        .group_by(action_domain.code, action_domain.name)
    )
    by_action = _count_map(db, _apply_access_event_filters(action_statement, **filters))

    person_statement = (
        select(func.coalesce(Person.person_type, "NAO_RESOLVIDA"), func.count(AccessEvent.id))
        .select_from(AccessEvent)
        .outerjoin(Person, Person.id == AccessEvent.person_id)
        .group_by(Person.person_type)
    )
    by_person_type = _count_map(db, _apply_access_event_filters(person_statement, **filters))

    total_by_status = {"matched": 0, "not_found": 0, **by_status}
    total_by_source = {"manual": 0, "upload": 0, **by_origin}
    return {
        "total": total,
        "by_status": by_status,
        "by_origin": by_origin,
        "by_action": by_action,
        "by_person_type": by_person_type,
        "total_events": total,
        "total_matched": total_by_status.get("matched", 0),
        "total_not_found": total_by_status.get("not_found", 0),
        "total_manual": total_by_source.get("manual", 0),
        "total_upload": total_by_source.get("upload", 0),
        "total_by_status": total_by_status,
        "total_by_source": total_by_source,
    }


def create_access_event(db: Session, data: dict[str, object]) -> AccessEvent:
    access_event = AccessEvent(**data)
    db.add(access_event)
    return access_event
