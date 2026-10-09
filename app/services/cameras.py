from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.access_point import AccessPoint
from app.models.camera import Camera
from app.repositories import cameras as camera_repository
from app.schemas.camera import CameraCreate, CameraUpdate
from app.services import access_points as access_point_service


@dataclass(frozen=True)
class ReadLocation:
    camera: Camera | None
    access_point: AccessPoint | None


def _normalize(data: dict[str, object]) -> dict[str, object]:
    for field in ("name", "description"):
        if isinstance(data.get(field), str):
            data[field] = str(data[field]).strip() or None
    if isinstance(data.get("code"), str):
        data["code"] = str(data["code"]).strip().upper()
    return data


def _commit(db: Session, camera: Camera) -> Camera:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Camera data conflicts with an existing record.",
            status_code=409,
            code="camera_code_conflict",
        ) from None
    db.refresh(camera)
    return camera


def list_cameras(
    db: Session, *, is_active: bool | None = None,
    access_point_id: int | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Camera]:
    return camera_repository.list_cameras(
        db, is_active=is_active, access_point_id=access_point_id,
        name=name, skip=skip, limit=limit,
    )


def get_camera_or_404(db: Session, camera_id: int) -> Camera:
    camera = camera_repository.get_camera(db, camera_id)
    if camera is None:
        raise AppException(
            "Camera was not found.", status_code=404, code="camera_not_found"
        )
    return camera


def _ensure_unique_code(
    db: Session, code: str, *, current_id: int | None = None
) -> None:
    duplicate = camera_repository.get_camera_by_code(db, code)
    if duplicate is not None and duplicate.id != current_id:
        raise AppException(
            "A camera with the same code already exists.",
            status_code=409,
            code="camera_code_conflict",
        )


def create_camera(db: Session, payload: CameraCreate) -> Camera:
    data = _normalize(payload.model_dump())
    access_point = access_point_service.get_access_point_or_404(
        db, payload.access_point_id
    )
    if payload.is_active and not access_point.is_active:
        raise AppException(
            "An active camera requires an active access point.",
            status_code=422,
            code="inactive_access_point",
        )
    _ensure_unique_code(db, str(data["code"]))
    return _commit(db, camera_repository.create_camera(db, data))


def update_camera(
    db: Session, camera_id: int, payload: CameraUpdate
) -> Camera:
    camera = get_camera_or_404(db, camera_id)
    changes = _normalize(payload.model_dump(exclude_unset=True))
    access_point_id = int(changes.get("access_point_id", camera.access_point_id))
    is_active = bool(changes.get("is_active", camera.is_active))
    access_point = access_point_service.get_access_point_or_404(db, access_point_id)
    if is_active and not access_point.is_active:
        raise AppException(
            "An active camera requires an active access point.",
            status_code=422,
            code="inactive_access_point",
        )
    code = str(changes.get("code", camera.code))
    _ensure_unique_code(db, code, current_id=camera.id)
    camera_repository.update_camera(camera, changes)
    return _commit(db, camera)


def deactivate_camera(db: Session, camera_id: int) -> None:
    camera = get_camera_or_404(db, camera_id)
    camera_repository.deactivate_camera(camera)
    db.commit()


def resolve_read_location(
    db: Session, *, camera_id: int | None, access_point_id: int | None
) -> ReadLocation:
    camera = None
    access_point = None
    if camera_id is not None:
        camera = get_camera_or_404(db, camera_id)
        if not camera.is_active:
            raise AppException(
                "Camera is inactive.", status_code=422, code="inactive_camera"
            )
        access_point = camera.access_point
        if access_point is None:
            raise AppException(
                "Camera does not reference a valid access point.",
                status_code=422,
                code="camera_access_point_invalid",
            )
        if access_point_id is not None and access_point.id != access_point_id:
            raise AppException(
                "camera_id and access_point_id reference different access points.",
                status_code=422,
                code="camera_access_point_mismatch",
            )
        if not access_point.is_active:
            raise AppException(
                "Access point is inactive.",
                status_code=422,
                code="inactive_access_point",
            )
    elif access_point_id is not None:
        access_point = access_point_service.get_active_access_point_or_error(
            db, access_point_id
        )
    return ReadLocation(camera=camera, access_point=access_point)
