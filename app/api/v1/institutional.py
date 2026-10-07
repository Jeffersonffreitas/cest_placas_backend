from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.integrations.institutional import (
    InstitutionalPersonProvider,
    get_institutional_person_provider,
)
from app.schemas.institutional import InstitutionalPersonRead
from app.schemas.person import PersonRead
from app.services import institutional as institutional_service


router = APIRouter(tags=["institutional"])
ProviderDependency = Annotated[
    InstitutionalPersonProvider, Depends(get_institutional_person_provider)
]


@router.get(
    "/people/{registration}",
    response_model=InstitutionalPersonRead,
    summary="Find a person in the institutional provider",
)
def find_institutional_person(
    registration: str,
    admin_user: CurrentAdminUser,
    provider: ProviderDependency,
) -> InstitutionalPersonRead:
    del admin_user
    return institutional_service.resolve_institutional_person(registration, provider)


@router.post(
    "/people/{registration}/sync",
    response_model=PersonRead,
    summary="Synchronize an institutional person with the local database",
)
def sync_institutional_person(
    registration: str,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    provider: ProviderDependency,
) -> PersonRead:
    del admin_user
    return PersonRead.model_validate(
        institutional_service.sync_institutional_person(db, registration, provider)
    )
