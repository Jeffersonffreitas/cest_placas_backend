from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services import vehicles as vehicle_service


router = APIRouter(tags=["vehicles"])


@router.post(
    "",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create vehicle",
)
def create_vehicle(
    payload: VehicleCreate,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> VehicleRead:
    del admin_user
    return VehicleRead.model_validate(vehicle_service.create_vehicle(db, payload))


@router.get(
    "",
    response_model=list[VehicleRead],
    status_code=status.HTTP_200_OK,
    summary="List vehicles",
)
def list_vehicles(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    student_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[VehicleRead]:
    del admin_user
    vehicles = vehicle_service.list_vehicles(
        db,
        skip=skip,
        limit=limit,
        student_id=student_id,
    )
    return [VehicleRead.model_validate(vehicle) for vehicle in vehicles]


@router.get(
    "/by-plate/{plate}",
    response_model=VehicleRead,
    status_code=status.HTTP_200_OK,
    summary="Get vehicle by plate",
)
def get_vehicle_by_plate(
    plate: str,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> VehicleRead:
    del admin_user
    return VehicleRead.model_validate(vehicle_service.get_vehicle_by_plate_or_404(db, plate))


@router.get(
    "/{vehicle_id}",
    response_model=VehicleRead,
    status_code=status.HTTP_200_OK,
    summary="Get vehicle by id",
)
def get_vehicle(
    vehicle_id: int,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> VehicleRead:
    del admin_user
    return VehicleRead.model_validate(vehicle_service.get_vehicle_or_404(db, vehicle_id))


@router.put(
    "/{vehicle_id}",
    response_model=VehicleRead,
    status_code=status.HTTP_200_OK,
    summary="Update vehicle",
)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> VehicleRead:
    del admin_user
    return VehicleRead.model_validate(vehicle_service.update_vehicle(db, vehicle_id, payload))


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate vehicle",
)
def delete_vehicle(
    vehicle_id: int,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    vehicle_service.delete_vehicle(db, vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
