from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.access_event import AccessEvent
from app.repositories import access_events as access_event_repository
from app.schemas.access_event import (
    AccessEventSource,
    AccessEventStatus,
    AccessEventSummaryPeriod,
    AccessEventSummaryRead,
)
from app.services.plates import normalize_and_validate_plate


def _validate_date_range(date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise AppException(
            "date_from must be less than or equal to date_to.",
            status_code=400,
            code="invalid_date_range",
        )


def list_access_events(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    plate: str | None = None,
    source: AccessEventSource | None = None,
    status: AccessEventStatus | None = None,
    student_id: int | None = None,
    vehicle_id: int | None = None,
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
        source=source,
        status=status,
        student_id=student_id,
        vehicle_id=vehicle_id,
        date_from=date_from,
        date_to=date_to,
    )


def summarize_access_events(
    db: Session,
    *,
    source: AccessEventSource | None = None,
    status: AccessEventStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AccessEventSummaryRead:
    _validate_date_range(date_from, date_to)

    summary_data = access_event_repository.summarize_access_events(
        db,
        source=source,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    period = None
    if date_from is not None or date_to is not None:
        period = AccessEventSummaryPeriod(date_from=date_from, date_to=date_to)
    return AccessEventSummaryRead(**summary_data, period=period)
