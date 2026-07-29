from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.domain import DomainCreate, DomainRead, DomainUpdate
from app.services import domains as domain_service


router = APIRouter(tags=["domains"])


@router.get("", response_model=list[DomainRead], summary="List domains")
def list_domains(
    admin_user: CurrentAdminUser, db: Annotated[Session, Depends(get_db)],
    tipo: Annotated[str | None, Query(min_length=1)] = None,
    ativo: Annotated[bool | None, Query()] = None,
    parent_id: Annotated[int | None, Query(gt=0)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[DomainRead]:
    del admin_user
    domains = domain_service.list_domains(
        db, type=tipo, is_active=ativo, parent_id=parent_id, skip=skip, limit=limit
    )
    return [DomainRead.model_validate(domain) for domain in domains]


@router.get("/{domain_id}", response_model=DomainRead, summary="Get domain by id")
def get_domain(
    domain_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DomainRead:
    del admin_user
    return DomainRead.model_validate(domain_service.get_domain_or_404(db, domain_id))


@router.post(
    "", response_model=DomainRead, status_code=status.HTTP_201_CREATED,
    summary="Create domain",
)
def create_domain(
    payload: DomainCreate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DomainRead:
    del admin_user
    return DomainRead.model_validate(domain_service.create_domain(db, payload))


@router.put("/{domain_id}", response_model=DomainRead, summary="Update domain")
def update_domain(
    domain_id: int, payload: DomainUpdate, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DomainRead:
    del admin_user
    return DomainRead.model_validate(domain_service.update_domain(db, domain_id, payload))


@router.delete(
    "/{domain_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate domain",
)
def delete_domain(
    domain_id: int, admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    domain_service.deactivate_domain(db, domain_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
