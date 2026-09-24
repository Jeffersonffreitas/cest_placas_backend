from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.access_event import (
    AccessEventCreate,
    AccessEventListItem,
    AccessEventRead,
    AccessEventSource,
    AccessEventStatsRead,
    AccessEventStatus,
    AccessEventSummaryRead,
)
from app.schemas.person import PersonType
from app.services import access_events as access_event_service


router = APIRouter(tags=["access-events"])


def _origin_filter(source: str | None, origin: str | None) -> str | None:
    return origin if origin is not None else source


@router.get(
    "/summary",
    response_model=AccessEventSummaryRead,
    status_code=status.HTTP_200_OK,
    summary="Summarize access events",
)
def summarize_access_events(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    plate: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    source: AccessEventSource | None = None,
    origin: Annotated[str | None, Query(min_length=1, max_length=30)] = None,
    access_status: Annotated[AccessEventStatus | None, Query(alias="status")] = None,
    person_id: Annotated[int | None, Query(gt=0)] = None,
    person_type: PersonType | None = None,
    vehicle_id: Annotated[int | None, Query(gt=0)] = None,
    action_id: Annotated[int | None, Query(gt=0)] = None,
    origin_id: Annotated[int | None, Query(gt=0)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> AccessEventSummaryRead:
    del admin_user
    return access_event_service.summarize_access_events(
        db,
        plate=plate,
        origin=_origin_filter(source, origin),
        status=access_status,
        person_id=person_id,
        person_type=person_type,
        vehicle_id=vehicle_id,
        action_id=action_id,
        origin_id=origin_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/recent",
    response_model=list[AccessEventListItem],
    status_code=status.HTTP_200_OK,
    summary="List recent access events",
)
def list_recent_access_events(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    access_status: Annotated[AccessEventStatus | None, Query(alias="status")] = None,
    person_type: PersonType | None = None,
    origin_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[AccessEventListItem]:
    del admin_user
    events = access_event_service.list_recent_access_events(
        db,
        limit=limit,
        status=access_status,
        person_type=person_type,
        origin_id=origin_id,
    )
    return [AccessEventListItem.model_validate(event) for event in events]


@router.get(
    "/stats",
    response_model=AccessEventStatsRead,
    status_code=status.HTTP_200_OK,
    summary="Get today's operational access-event indicators",
)
def get_access_event_stats(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AccessEventStatsRead:
    del admin_user
    return access_event_service.get_access_event_stats(db)


@router.post(
    "",
    response_model=AccessEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an access event from a plate",
)
def create_access_event(
    payload: AccessEventCreate,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AccessEventRead:
    del admin_user
    return AccessEventRead.model_validate(
        access_event_service.create_access_event(db, payload)
    )


@router.get(
    "",
    response_model=list[AccessEventListItem],
    status_code=status.HTTP_200_OK,
    summary="List access events",
)
def list_access_events(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    plate: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    source: AccessEventSource | None = None,
    origin: Annotated[str | None, Query(min_length=1, max_length=30)] = None,
    access_status: Annotated[AccessEventStatus | None, Query(alias="status")] = None,
    person_id: Annotated[int | None, Query(gt=0)] = None,
    student_id: Annotated[int | None, Query(gt=0)] = None,
    person_type: PersonType | None = None,
    vehicle_id: Annotated[int | None, Query(gt=0)] = None,
    action_id: Annotated[int | None, Query(gt=0)] = None,
    origin_id: Annotated[int | None, Query(gt=0)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[AccessEventListItem]:
    del admin_user
    events = access_event_service.list_access_events(
        db,
        skip=skip,
        limit=limit,
        plate=plate,
        origin=_origin_filter(source, origin),
        status=access_status,
        person_id=person_id if person_id is not None else student_id,
        person_type=person_type,
        vehicle_id=vehicle_id,
        action_id=action_id,
        origin_id=origin_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [AccessEventListItem.model_validate(event) for event in events]


@router.get(
    "/{access_event_id}",
    response_model=AccessEventRead,
    status_code=status.HTTP_200_OK,
    summary="Get an access event",
)
def get_access_event(
    access_event_id: int,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AccessEventRead:
    del admin_user
    return AccessEventRead.model_validate(
        access_event_service.get_access_event_or_404(db, access_event_id)
    )
