from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.coordination import Coordination


def list_coordinations(
    db: Session, *, is_active: bool | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Coordination]:
    statement = select(Coordination)
    if is_active is not None:
        statement = statement.where(Coordination.is_active.is_(is_active))
    if name is not None:
        statement = statement.where(
            func.lower(Coordination.name).like(f"%{name.lower()}%")
        )
    statement = statement.order_by(Coordination.name, Coordination.id)
    return list(db.scalars(statement.offset(skip).limit(limit)).all())


def get_by_identity(
    db: Session, *, acronym: str | None, name: str,
) -> Coordination | None:
    if acronym is not None:
        match = db.scalar(
            select(Coordination)
            .where(func.lower(Coordination.acronym) == acronym.lower())
            .order_by(Coordination.id)
        )
        if match is not None:
            return match
    return db.scalar(
        select(Coordination)
        .where(func.lower(Coordination.name) == name.lower())
        .order_by(Coordination.id)
    )


def create_coordination(db: Session, data: dict[str, object]) -> Coordination:
    coordination = Coordination(**data)
    db.add(coordination)
    return coordination
