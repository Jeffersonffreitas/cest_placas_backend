from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.plate import (
    ImagePlateReadResponse,
    ManualPlateReadRequest,
    ManualPlateReadResponse,
)
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead
from app.services import plates as plate_service


router = APIRouter(tags=["plates"])


@router.post(
    "/read-manual",
    response_model=ManualPlateReadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register manual plate read",
)
def read_manual_plate(
    payload: ManualPlateReadRequest,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> ManualPlateReadResponse:
    del admin_user
    access_event = plate_service.read_manual_plate(db, payload)
    return ManualPlateReadResponse(
        id=access_event.id,
        plate_input=access_event.plate_input,
        plate_normalized=access_event.plate_normalized,
        source=access_event.source,
        status=access_event.status,
        vehicle=VehicleRead.model_validate(access_event.vehicle) if access_event.vehicle else None,
        student=StudentRead.model_validate(access_event.student) if access_event.student else None,
        created_at=access_event.created_at,
    )


@router.post(
    "/read-image",
    response_model=ImagePlateReadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register plate read from uploaded image",
)
def read_image_plate(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    mock_plate: str | None = Form(default=None),
) -> ImagePlateReadResponse:
    del admin_user
    result = plate_service.read_image_plate(db, file, mock_plate)
    access_event = result.access_event
    return ImagePlateReadResponse(
        id=access_event.id,
        plate_input=access_event.plate_input,
        plate_normalized=access_event.plate_normalized,
        source=access_event.source,
        status=access_event.status,
        vehicle=VehicleRead.model_validate(access_event.vehicle) if access_event.vehicle else None,
        student=StudentRead.model_validate(access_event.student) if access_event.student else None,
        image_path=result.image_path,
        confidence=result.confidence,
        created_at=access_event.created_at,
    )
