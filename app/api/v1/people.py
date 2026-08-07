from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.person import PersonCreate, PersonListItem, PersonRead, PersonUpdate
from app.schemas.vehicle import VehicleRead
from app.services import people as person_service
from app.services import person_vehicles as link_service


router = APIRouter(tags=["people"])


@router.get("", response_model=list[PersonListItem], summary="List people")
def list_people(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    person_type: Annotated[Literal["ALUNO", "FUNCIONARIO"] | None, Query()] = None,
    registration_number: Annotated[str | None, Query(min_length=1)] = None,
    active: Annotated[bool | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PersonListItem]:
    del admin_user
    people = person_service.list_people(
        db, person_type=person_type, registration_number=registration_number,
        is_active=active, skip=skip, limit=limit,
    )
    return [PersonListItem.model_validate(person) for person in people]


@router.get(
    "/by-registration/{registration_number}", response_model=PersonRead,
    summary="Get person by registration number",
)
def get_person_by_registration_number(
    registration_number: str,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    del admin_user
    return PersonRead.model_validate(
        person_service.get_person_by_registration_number_or_404(
            db, registration_number
        )
    )


@router.get("/{person_id}", response_model=PersonRead, summary="Get person by id")
def get_person(
    person_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    del admin_user
    return PersonRead.model_validate(person_service.get_person_or_404(db, person_id))


@router.post(
    "", response_model=PersonRead, status_code=status.HTTP_201_CREATED,
    summary="Create person",
)
def create_person(
    payload: PersonCreate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    del admin_user
    return PersonRead.model_validate(person_service.create_person(db, payload))


@router.put("/{person_id}", response_model=PersonRead, summary="Update person")
def update_person(
    person_id: int, payload: PersonUpdate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PersonRead:
    del admin_user
    return PersonRead.model_validate(
        person_service.update_person(db, person_id, payload)
    )


@router.delete(
    "/{person_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate person",
)
def delete_person(
    person_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    person_service.delete_person(db, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{person_id}/vehicles", response_model=list[VehicleRead],
    summary="List vehicles linked to a person",
)
def list_person_vehicles(
    person_id: int,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[VehicleRead]:
    del admin_user
    vehicles = link_service.list_vehicles_for_person(
        db, person_id, skip=skip, limit=limit
    )
    return [VehicleRead.model_validate(vehicle) for vehicle in vehicles]
