from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.access_event import AccessEventRead
from app.schemas.access_context import VehicleSide
from app.schemas.person import PersonRead
from app.schemas.plate import (
    ImagePlateReadResponse,
    ManualPlateReadRequest,
    ManualPlateReadResponse,
)
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead
from app.services import plates as plate_service


router = APIRouter(tags=["plates"])


def _operational_response_data(
    access_event, *, confidence: float | None = None
) -> dict[str, object]:
    decision = plate_service.operational_decision_for_access_event(access_event)
    plate_read = access_event.plate_read
    camera = plate_read.camera if plate_read is not None else None
    access_point = access_event.access_point
    return {
        "message": plate_service.operational_message(decision),
        "id": access_event.id,
        "access_event_id": access_event.id,
        "plate_read_id": access_event.plate_read_id,
        "plate_input": access_event.plate_input,
        "plate_normalized": access_event.plate_normalized,
        "source": access_event.source,
        "confidence": confidence,
        "status": access_event.status,
        "operational_decision": decision,
        "vehicle_side": (
            plate_read.vehicle_side if plate_read is not None else "INDEFINIDO"
        ),
        "camera": (
            {"id": camera.id, "name": camera.name} if camera is not None else None
        ),
        "access_point": (
            {
                "id": access_point.id,
                "name": access_point.name,
                "direction": access_point.direction,
            }
            if access_point is not None
            else None
        ),
        "access_event": AccessEventRead.model_validate(access_event),
        "vehicle": VehicleRead.model_validate(access_event.vehicle)
        if access_event.vehicle
        else None,
        "person": PersonRead.model_validate(access_event.person)
        if access_event.person
        else None,
        "person_type": access_event.person.person_type if access_event.person else None,
        "action": plate_service.access_event_action(access_event),
        "origin": plate_service.access_event_origin(access_event),
        "student": StudentRead.model_validate(access_event.student)
        if access_event.student
        else None,
        "created_at": access_event.created_at,
    }


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
    return ManualPlateReadResponse(**_operational_response_data(access_event))


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
    camera_id: int | None = Form(default=None, gt=0),
    access_point_id: int | None = Form(default=None, gt=0),
    vehicle_side: VehicleSide = Form(default="INDEFINIDO"),
) -> ImagePlateReadResponse:
    del admin_user
    result = plate_service.read_image_plate(
        db,
        file,
        mock_plate,
        camera_id=camera_id,
        access_point_id=access_point_id,
        vehicle_side=vehicle_side,
    )
    access_event = result.access_event
    response_data = _operational_response_data(
        access_event, confidence=result.confidence
    )
    response_data["operational_decision"] = result.operational_decision
    response_data["message"] = plate_service.operational_message(
        result.operational_decision
    )
    return ImagePlateReadResponse(**response_data, image_path=result.image_path)
