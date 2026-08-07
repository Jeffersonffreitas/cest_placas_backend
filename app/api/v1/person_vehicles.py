from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.person_vehicle import (
    PersonVehicleCreate, PersonVehicleListItem, PersonVehicleRead,
)
from app.services import person_vehicles as link_service


router = APIRouter(tags=["person-vehicles"])


@router.get("", response_model=list[PersonVehicleListItem], summary="List person-vehicle links")
def list_person_vehicles(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    person_id: Annotated[int | None, Query(gt=0)] = None,
    vehicle_id: Annotated[int | None, Query(gt=0)] = None,
    active: Annotated[bool | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PersonVehicleListItem]:
    del admin_user
    links = link_service.list_person_vehicles(
        db, person_id=person_id, vehicle_id=vehicle_id, is_active=active,
        skip=skip, limit=limit,
    )
    return [PersonVehicleListItem.model_validate(link) for link in links]


@router.post(
    "", response_model=PersonVehicleRead, status_code=status.HTTP_201_CREATED,
    summary="Create person-vehicle link",
)
def create_person_vehicle(
    payload: PersonVehicleCreate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PersonVehicleRead:
    del admin_user
    return PersonVehicleRead.model_validate(
        link_service.create_person_vehicle(db, payload)
    )


@router.get(
    "/{person_vehicle_id}", response_model=PersonVehicleRead,
    summary="Get person-vehicle link by id",
)
def get_person_vehicle(
    person_vehicle_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PersonVehicleRead:
    del admin_user
    return PersonVehicleRead.model_validate(
        link_service.get_person_vehicle_or_404(db, person_vehicle_id)
    )


@router.delete(
    "/{person_vehicle_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate person-vehicle link",
)
def delete_person_vehicle(
    person_vehicle_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    link_service.delete_person_vehicle(db, person_vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
