from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.coordination import CoordinationRead
from app.services import coordinations as coordination_service


router = APIRouter(tags=["coordinations"])


@router.get("", response_model=list[CoordinationRead], summary="List coordinations")
def list_coordinations(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    active: Annotated[bool | None, Query()] = None,
    name: Annotated[str | None, Query(min_length=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[CoordinationRead]:
    del admin_user
    rows = coordination_service.list_coordinations(
        db, is_active=active, name=name, skip=skip, limit=limit
    )
    return [CoordinationRead.model_validate(row) for row in rows]
