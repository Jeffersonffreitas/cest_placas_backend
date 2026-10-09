from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.access_point import AccessPoint
from app.repositories import access_points as access_point_repository
from app.schemas.access_point import AccessPointCreate, AccessPointUpdate
from app.schemas.access_context import AccessPointDirection


def _normalize(data: dict[str, object]) -> dict[str, object]:
    for field in ("name", "description"):
        if isinstance(data.get(field), str):
            data[field] = str(data[field]).strip() or None
    if isinstance(data.get("code"), str):
        data["code"] = str(data["code"]).strip().upper() or None
    if isinstance(data.get("direction"), str):
        data["direction"] = str(data["direction"]).strip().upper()
    return data


def _commit(db: Session, access_point: AccessPoint) -> AccessPoint:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Access point data conflicts with an existing record.",
            status_code=409,
            code="access_point_conflict",
        ) from None
    db.refresh(access_point)
    return access_point


def list_access_points(
    db: Session, *, is_active: bool | None = None,
    direction: AccessPointDirection | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[AccessPoint]:
    return access_point_repository.list_access_points(
        db, is_active=is_active, direction=direction, name=name,
        skip=skip, limit=limit,
    )


def get_access_point_or_404(db: Session, access_point_id: int) -> AccessPoint:
    access_point = access_point_repository.get_access_point(db, access_point_id)
    if access_point is None:
        raise AppException(
            "Access point was not found.",
            status_code=404,
            code="access_point_not_found",
        )
    return access_point


def get_active_access_point_or_error(
    db: Session, access_point_id: int
) -> AccessPoint:
    access_point = get_access_point_or_404(db, access_point_id)
    if not access_point.is_active:
        raise AppException(
            "Access point is inactive.",
            status_code=422,
            code="inactive_access_point",
        )
    return access_point


def create_access_point(
    db: Session, payload: AccessPointCreate
) -> AccessPoint:
    data = _normalize(payload.model_dump())
    return _commit(db, access_point_repository.create_access_point(db, data))


def update_access_point(
    db: Session, access_point_id: int, payload: AccessPointUpdate
) -> AccessPoint:
    access_point = get_access_point_or_404(db, access_point_id)
    changes = _normalize(payload.model_dump(exclude_unset=True))
    access_point_repository.update_access_point(access_point, changes)
    return _commit(db, access_point)


def deactivate_access_point(db: Session, access_point_id: int) -> None:
    access_point = get_access_point_or_404(db, access_point_id)
    access_point_repository.deactivate_access_point(access_point)
    db.commit()
