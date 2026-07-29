from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.domain import Domain
from app.repositories import domains as domain_repository
from app.schemas.domain import DomainCreate, DomainUpdate


def _normalize(data: dict[str, object]) -> dict[str, object]:
    if isinstance(data.get("type"), str):
        data["type"] = str(data["type"]).strip().upper()
    if isinstance(data.get("code"), str):
        data["code"] = str(data["code"]).strip().upper() or None
    if isinstance(data.get("name"), str):
        data["name"] = str(data["name"]).strip()
    return data


def list_domains(
    db: Session, *, type: str | None = None, is_active: bool | None = None,
    parent_id: int | None = None, skip: int = 0, limit: int = 100,
) -> list[Domain]:
    normalized_type = type.strip().upper() if type is not None else None
    return domain_repository.list_domains(
        db, type=normalized_type, is_active=is_active, parent_id=parent_id,
        skip=skip, limit=limit,
    )


def get_domain_or_404(db: Session, domain_id: int) -> Domain:
    domain = domain_repository.get_domain(db, domain_id)
    if domain is None:
        raise AppException("Domain was not found.", status_code=404, code="domain_not_found")
    return domain


def _validate_parent(db: Session, parent_id: int | None, current_id: int | None = None) -> None:
    if parent_id is None:
        return
    if parent_id == current_id:
        raise AppException(
            "A domain cannot be its own parent.", status_code=409, code="domain_parent_conflict"
        )
    get_domain_or_404(db, parent_id)


def _ensure_no_active_duplicate(
    db: Session, data: dict[str, object], *, current_id: int | None = None,
) -> None:
    if not bool(data["is_active"]):
        return
    duplicate = domain_repository.get_active_duplicate(
        db, type=str(data["type"]),
        code=data.get("code") if isinstance(data.get("code"), str) else None,
        name=str(data["name"]),
    )
    if duplicate is not None and duplicate.id != current_id:
        raise AppException(
            "An active domain option with the same identity already exists.",
            status_code=409, code="domain_conflict",
        )


def _commit(db: Session, domain: Domain) -> Domain:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Domain data conflicts with an existing record.",
            status_code=409, code="domain_conflict",
        ) from None
    db.refresh(domain)
    return domain


def create_domain(db: Session, payload: DomainCreate) -> Domain:
    data = _normalize(payload.model_dump())
    parent_id = data.get("parent_id") if isinstance(data.get("parent_id"), int) else None
    _validate_parent(db, parent_id)
    _ensure_no_active_duplicate(db, data)
    return _commit(db, domain_repository.create_domain(db, data))


def update_domain(db: Session, domain_id: int, payload: DomainUpdate) -> Domain:
    domain = get_domain_or_404(db, domain_id)
    changes = _normalize(payload.model_dump(exclude_unset=True))
    merged = {
        "type": changes.get("type", domain.type), "code": changes.get("code", domain.code),
        "name": changes.get("name", domain.name),
        "parent_id": changes.get("parent_id", domain.parent_id),
        "is_active": changes.get("is_active", domain.is_active),
    }
    parent_id = merged["parent_id"] if isinstance(merged["parent_id"], int) else None
    _validate_parent(db, parent_id, domain.id)
    _ensure_no_active_duplicate(db, merged, current_id=domain.id)
    domain_repository.update_domain(domain, changes)
    return _commit(db, domain)


def deactivate_domain(db: Session, domain_id: int) -> None:
    domain = get_domain_or_404(db, domain_id)
    domain_repository.deactivate_domain(domain)
    db.commit()
