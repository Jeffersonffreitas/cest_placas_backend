from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.access_event import AccessEvent
from app.models.domain import Domain
from app.models.person import Person
from app.models.vehicle import Vehicle


def _apply_access_event_filters(
    statement,
    *,
    plate_normalized: str | None = None,
    origin: str | None = None,
    status: str | None = None,
    person_id: int | None = None,
    person_type: str | None = None,
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
    if person_type is not None:
        statement = statement.where(
            AccessEvent.person.has(Person.person_type == person_type)
        )
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
        joinedload(AccessEvent.vehicle).joinedload(Vehicle.brand_domain),
        joinedload(AccessEvent.vehicle).joinedload(Vehicle.model_domain),
        joinedload(AccessEvent.vehicle).joinedload(Vehicle.color_domain),
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
    counts: dict[str, int] = {}
    for key, total in db.execute(statement).all():
        normalized_key = str(key) if key is not None else "NAO_INFORMADO"
        counts[normalized_key] = counts.get(normalized_key, 0) + int(total)
    return counts


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

    textual_source_statement = (
        select(AccessEvent.origin, func.count(AccessEvent.id))
        .group_by(AccessEvent.origin)
    )
    textual_sources = _count_map(
        db, _apply_access_event_filters(textual_source_statement, **filters)
    )
    total_by_status = {"matched": 0, "not_found": 0, **by_status}
    total_by_source = {"manual": 0, "upload": 0, **textual_sources}
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
        "total_access_granted": by_status.get("ACESSO_LIBERADO", 0),
        "total_vehicle_not_registered": by_status.get(
            "VEICULO_NAO_CADASTRADO", 0
        ),
        "total_person_not_linked": by_status.get("PESSOA_NAO_VINCULADA", 0),
        "total_invalid_plate": by_status.get("PLACA_INVALIDA", 0),
        "total_low_confidence": by_status.get("OCR_BAIXA_CONFIANCA", 0),
        "total_ocr_error": by_status.get("ERRO_OCR", 0),
    }


def get_access_event_stats(
    db: Session, *, date_from: datetime, date_to: datetime
) -> dict[str, int]:
    """Return today's indicators in one aggregate query without multiplicative joins."""
    in_period = (
        AccessEvent.created_at >= date_from,
        AccessEvent.created_at < date_to,
    )
    statement = select(
        func.count(AccessEvent.id).label("total_today"),
        func.coalesce(
            func.sum(case((AccessEvent.status == "ACESSO_LIBERADO", 1), else_=0)),
            0,
        ).label("access_granted_today"),
        func.coalesce(
            func.sum(case((AccessEvent.status != "ACESSO_LIBERADO", 1), else_=0)),
            0,
        ).label("unresolved_today"),
        func.count(func.distinct(AccessEvent.vehicle_id)).label(
            "unique_vehicles_today"
        ),
        func.count(func.distinct(AccessEvent.person_id)).label("unique_people_today"),
        func.coalesce(
            func.sum(
                case(
                    (AccessEvent.person.has(Person.person_type == "ALUNO"), 1),
                    else_=0,
                )
            ),
            0,
        ).label("students_today"),
        func.coalesce(
            func.sum(
                case(
                    (AccessEvent.person.has(Person.person_type == "FUNCIONARIO"), 1),
                    else_=0,
                )
            ),
            0,
        ).label("employees_today"),
        func.coalesce(
            func.sum(
                case(
                    (AccessEvent.person.has(Person.person_type == "VISITANTE"), 1),
                    else_=0,
                )
            ),
            0,
        ).label("visitors_today"),
    ).where(*in_period)
    row = db.execute(statement).one()._mapping
    return {key: int(value or 0) for key, value in row.items()}


def create_access_event(db: Session, data: dict[str, object]) -> AccessEvent:
    access_event = AccessEvent(**data)
    db.add(access_event)
    return access_event
