from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.domain import Domain


def list_domains(
    db: Session, *, type: str | None = None, is_active: bool | None = None,
    parent_id: int | None = None, skip: int = 0, limit: int = 100,
) -> list[Domain]:
    statement = select(Domain)
    if type is not None:
        statement = statement.where(Domain.type == type)
    if is_active is not None:
        statement = statement.where(Domain.is_active.is_(is_active))
    if parent_id is not None:
        statement = statement.where(Domain.parent_id == parent_id)
    statement = statement.order_by(Domain.type, Domain.name, Domain.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_domain(db: Session, domain_id: int) -> Domain | None:
    return db.get(Domain, domain_id)


def get_active_duplicate(
    db: Session, *, type: str, code: str | None, name: str,
) -> Domain | None:
    identity = Domain.code == code if code is not None else and_(
        Domain.code.is_(None), Domain.name == name
    )
    statement = select(Domain).where(
        Domain.type == type, Domain.is_active.is_(True), identity,
    )
    return db.scalars(statement).first()


def create_domain(db: Session, data: dict[str, object]) -> Domain:
    domain = Domain(**data)
    db.add(domain)
    return domain


def update_domain(domain: Domain, data: dict[str, object]) -> Domain:
    for field, value in data.items():
        setattr(domain, field, value)
    return domain


def deactivate_domain(domain: Domain) -> Domain:
    domain.is_active = False
    return domain
