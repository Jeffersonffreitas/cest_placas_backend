from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.services import cameras as camera_service


router = APIRouter(tags=["cameras"])


@router.get("", response_model=list[CameraRead], summary="List logical cameras")
def list_cameras(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    active: Annotated[bool | None, Query()] = None,
    access_point_id: Annotated[int | None, Query(gt=0)] = None,
    name: Annotated[str | None, Query(min_length=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[CameraRead]:
    del admin_user
    items = camera_service.list_cameras(
        db, is_active=active, access_point_id=access_point_id,
        name=name, skip=skip, limit=limit,
    )
    return [CameraRead.model_validate(item) for item in items]


@router.get("/{camera_id}", response_model=CameraRead, summary="Get logical camera")
def get_camera(
    camera_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> CameraRead:
    del admin_user
    return CameraRead.model_validate(camera_service.get_camera_or_404(db, camera_id))


@router.post(
    "", response_model=CameraRead, status_code=status.HTTP_201_CREATED,
    summary="Create logical camera",
)
def create_camera(
    payload: CameraCreate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> CameraRead:
    del admin_user
    return CameraRead.model_validate(camera_service.create_camera(db, payload))


@router.put("/{camera_id}", response_model=CameraRead, summary="Update logical camera")
def update_camera(
    camera_id: int, payload: CameraUpdate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> CameraRead:
    del admin_user
    return CameraRead.model_validate(
        camera_service.update_camera(db, camera_id, payload)
    )


@router.delete(
    "/{camera_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate logical camera",
)
def delete_camera(
    camera_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    camera_service.deactivate_camera(db, camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
