from sqlalchemy.orm import Session

from app.models.coordination import Coordination
from app.repositories import coordinations as coordination_repository


def list_coordinations(
    db: Session, *, is_active: bool | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Coordination]:
    normalized_name = name.strip() if name is not None else None
    return coordination_repository.list_coordinations(
        db, is_active=is_active, name=normalized_name, skip=skip, limit=limit
    )
