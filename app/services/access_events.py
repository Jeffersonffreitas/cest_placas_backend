from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.access_event import AccessEvent
from app.models.domain import Domain
from app.models.person import Person
from app.models.plate_read import PlateRead
from app.repositories import access_events as access_event_repository
from app.repositories import domains as domain_repository
from app.repositories import person_vehicles as person_vehicle_repository
from app.repositories import vehicles as vehicle_repository
from app.schemas.access_event import (
    AccessEventCreate,
    AccessEventStatus,
    AccessEventSummaryPeriod,
    AccessEventSummaryRead,
)
from app.services.plate_utils import normalize_and_validate_plate


def _validate_date_range(date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise AppException(
            "date_from must be less than or equal to date_to.",
            status_code=400,
            code="invalid_date_range",
        )


def _validate_domain(
    db: Session, domain_id: int | None, expected_type: str, field: str
) -> Domain | None:
    if domain_id is None:
        return None
    domain = db.get(Domain, domain_id)
    if domain is None or not domain.is_active or domain.type != expected_type:
        raise AppException(
            f"{field} must reference an active {expected_type} domain.",
            status_code=422,
            code=f"invalid_{field}",
        )
    return domain


def _resolved_access_data(db: Session, plate_normalized: str) -> tuple[object | None, Person | None, str]:
    vehicle = vehicle_repository.get_vehicle_by_plate(db, plate_normalized)
    if vehicle is None:
        return None, None, "VEICULO_NAO_CADASTRADO"
    active_person = person_vehicle_repository.get_first_active_person_for_vehicle(
        db, vehicle.id
    )
    person = (
        active_person
        or person_vehicle_repository.get_first_person_with_active_link_for_vehicle(
            db, vehicle.id
        )
    )
    if not vehicle.is_active:
        return vehicle, person, "CADASTRO_INATIVO"
    if active_person is not None:
        return vehicle, active_person, "ACESSO_LIBERADO"
    if person is None:
        return vehicle, None, "PESSOA_NAO_VINCULADA"
    return vehicle, person, "CADASTRO_INATIVO"


def create_access_event_from_plate_read(
    db: Session,
    *,
    plate_input: str,
    plate_normalized: str,
    origin: str,
    plate_read_id: int,
    status_override: AccessEventStatus | None = None,
) -> AccessEvent:
    """Create the event paired with a manual or image plate read.

    Domain lookup is best-effort so an installation without the optional
    ACAO_ACESSO/ORIGEM_ACESSO rows can still register the access attempt.
    """
    vehicle = None
    person = None
    resolved_status: AccessEventStatus = status_override or "VEICULO_NAO_CADASTRADO"
    if status_override is None:
        vehicle, person, resolved_status = _resolved_access_data(db, plate_normalized)

    action_code = "ENTRADA" if resolved_status == "ACESSO_LIBERADO" else "TENTATIVA"
    origin_code = "TESTE_MANUAL" if origin == "manual" else "UPLOAD_IMAGEM"
    action = domain_repository.get_active_by_type_and_code(
        db, type="ACAO_ACESSO", code=action_code
    )
    origin_domain = domain_repository.get_active_by_type_and_code(
        db, type="ORIGEM_ACESSO", code=origin_code
    )
    return access_event_repository.create_access_event(
        db,
        {
            "vehicle_id": vehicle.id if vehicle is not None else None,
            "person_id": person.id if person is not None else None,
            "plate_read_id": plate_read_id,
            "action_id": action.id if action is not None else None,
            "origin_id": origin_domain.id if origin_domain is not None else None,
            "status": resolved_status,
            "plate_input": plate_input[:20],
            "plate_normalized": plate_normalized[:10],
            "origin": origin,
        },
    )


def create_resolved_access_event(
    db: Session,
    *,
    plate_input: str,
    origin: str,
    action_id: int | None = None,
    origin_id: int | None = None,
    plate_read_id: int | None = None,
    status_override: str | None = None,
) -> AccessEvent:
    plate_normalized = normalize_and_validate_plate(plate_input)
    vehicle, person, resolved_status = _resolved_access_data(db, plate_normalized)
    event = access_event_repository.create_access_event(
        db,
        {
            "vehicle_id": vehicle.id if vehicle is not None else None,
            "person_id": person.id if person is not None else None,
            "plate_read_id": plate_read_id,
            "action_id": action_id,
            "origin_id": origin_id,
            "status": status_override or resolved_status,
            "plate_input": plate_input,
            "plate_normalized": plate_normalized,
            "origin": origin,
        },
    )
    return event


def create_access_event(db: Session, payload: AccessEventCreate) -> AccessEvent:
    data = payload.model_dump()
    _validate_domain(db, payload.action_id, "ACAO_ACESSO", "action_id")
    origin_domain = _validate_domain(
        db, payload.origin_id, "ORIGEM_ACESSO", "origin_id"
    )
    if payload.vehicle_id is not None and vehicle_repository.get_vehicle(db, payload.vehicle_id) is None:
        raise AppException("Vehicle was not found.", status_code=404, code="vehicle_not_found")
    if payload.person_id is not None and db.get(Person, payload.person_id) is None:
        raise AppException("Person was not found.", status_code=404, code="person_not_found")
    if payload.plate_read_id is not None and db.get(PlateRead, payload.plate_read_id) is None:
        raise AppException("Plate read was not found.", status_code=404, code="plate_read_not_found")

    event = create_resolved_access_event(
        db,
        plate_input=payload.plate,
        origin=(origin_domain.code or origin_domain.name)
        if origin_domain
        else (payload.source or payload.origin),
        action_id=payload.action_id,
        origin_id=payload.origin_id,
        plate_read_id=payload.plate_read_id,
    )
    if payload.vehicle_id is not None and event.vehicle_id != payload.vehicle_id:
        db.rollback()
        raise AppException(
            "vehicle_id does not match the vehicle resolved from the plate.",
            status_code=422,
            code="vehicle_plate_mismatch",
        )
    if payload.person_id is not None and event.person_id != payload.person_id:
        db.rollback()
        raise AppException(
            "person_id does not match the active person resolved for the vehicle.",
            status_code=422,
            code="person_vehicle_mismatch",
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Access event data conflicts with an existing record.",
            status_code=409,
            code="access_event_conflict",
        ) from None
    return get_access_event_or_404(db, event.id)


def get_access_event_or_404(db: Session, access_event_id: int) -> AccessEvent:
    event = access_event_repository.get_access_event(db, access_event_id)
    if event is None:
        raise AppException(
            "Access event was not found.", status_code=404, code="access_event_not_found"
        )
    return event


def list_access_events(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    plate: str | None = None,
    origin: str | None = None,
    status: AccessEventStatus | None = None,
    person_id: int | None = None,
    vehicle_id: int | None = None,
    action_id: int | None = None,
    origin_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AccessEvent]:
    _validate_date_range(date_from, date_to)
    plate_normalized = normalize_and_validate_plate(plate) if plate is not None else None
    return access_event_repository.list_access_events(
        db,
        skip=skip,
        limit=limit,
        plate_normalized=plate_normalized,
        origin=origin,
        status=status,
        person_id=person_id,
        vehicle_id=vehicle_id,
        action_id=action_id,
        origin_id=origin_id,
        date_from=date_from,
        date_to=date_to,
    )


def summarize_access_events(
    db: Session,
    *,
    origin: str | None = None,
    status: AccessEventStatus | None = None,
    person_id: int | None = None,
    vehicle_id: int | None = None,
    action_id: int | None = None,
    origin_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AccessEventSummaryRead:
    _validate_date_range(date_from, date_to)
    summary_data = access_event_repository.summarize_access_events(
        db,
        origin=origin,
        status=status,
        person_id=person_id,
        vehicle_id=vehicle_id,
        action_id=action_id,
        origin_id=origin_id,
        date_from=date_from,
        date_to=date_to,
    )
    period = None
    if date_from is not None or date_to is not None:
        period = AccessEventSummaryPeriod(date_from=date_from, date_to=date_to)
    return AccessEventSummaryRead(**summary_data, period=period)
