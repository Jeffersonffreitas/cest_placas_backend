from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.access_event import AccessEventRead, AccessEventStatus
from app.services import access_events as access_event_service


router = APIRouter(tags=["access-events"])


@router.get(
    "",
    response_model=list[AccessEventRead],
    status_code=status.HTTP_200_OK,
    summary="List access events",
)
def list_access_events(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    plate: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    access_status: Annotated[AccessEventStatus | None, Query(alias="status")] = None,
    student_id: Annotated[int | None, Query(gt=0)] = None,
    vehicle_id: Annotated[int | None, Query(gt=0)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[AccessEventRead]:
    del admin_user
    access_events = access_event_service.list_access_events(
        db,
        skip=skip,
        limit=limit,
        plate=plate,
        status=access_status,
        student_id=student_id,
        vehicle_id=vehicle_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [AccessEventRead.model_validate(access_event) for access_event in access_events]
