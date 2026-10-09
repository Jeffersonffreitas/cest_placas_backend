from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.access_context import AccessPointDirection
from app.schemas.access_point import AccessPointCreate, AccessPointRead, AccessPointUpdate
from app.services import access_points as access_point_service


router = APIRouter(tags=["access-points"])


@router.get("", response_model=list[AccessPointRead], summary="List access points")
def list_access_points(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    active: Annotated[bool | None, Query()] = None,
    direction: AccessPointDirection | None = None,
    name: Annotated[str | None, Query(min_length=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AccessPointRead]:
    del admin_user
    items = access_point_service.list_access_points(
        db, is_active=active, direction=direction, name=name,
        skip=skip, limit=limit,
    )
    return [AccessPointRead.model_validate(item) for item in items]


@router.get("/{access_point_id}", response_model=AccessPointRead, summary="Get access point")
def get_access_point(
    access_point_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AccessPointRead:
    del admin_user
    return AccessPointRead.model_validate(
        access_point_service.get_access_point_or_404(db, access_point_id)
    )


@router.post(
    "", response_model=AccessPointRead, status_code=status.HTTP_201_CREATED,
    summary="Create access point",
)
def create_access_point(
    payload: AccessPointCreate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AccessPointRead:
    del admin_user
    return AccessPointRead.model_validate(
        access_point_service.create_access_point(db, payload)
    )


@router.put("/{access_point_id}", response_model=AccessPointRead, summary="Update access point")
def update_access_point(
    access_point_id: int, payload: AccessPointUpdate,
    admin_user: CurrentAdminUser, db: Annotated[Session, Depends(get_db)],
) -> AccessPointRead:
    del admin_user
    return AccessPointRead.model_validate(
        access_point_service.update_access_point(db, access_point_id, payload)
    )


@router.delete(
    "/{access_point_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate access point",
)
def delete_access_point(
    access_point_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    access_point_service.deactivate_access_point(db, access_point_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
