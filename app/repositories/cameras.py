from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.camera import Camera


def list_cameras(
    db: Session, *, is_active: bool | None = None,
    access_point_id: int | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Camera]:
    statement = select(Camera).options(joinedload(Camera.access_point))
    if is_active is not None:
        statement = statement.where(Camera.is_active.is_(is_active))
    if access_point_id is not None:
        statement = statement.where(Camera.access_point_id == access_point_id)
    if name is not None:
        statement = statement.where(func.lower(Camera.name).contains(name.strip().lower()))
    statement = statement.order_by(Camera.name, Camera.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_camera(db: Session, camera_id: int) -> Camera | None:
    statement = select(Camera).where(Camera.id == camera_id).options(
        joinedload(Camera.access_point)
    )
    return db.scalars(statement).first()


def get_camera_by_code(db: Session, code: str) -> Camera | None:
    return db.scalars(select(Camera).where(Camera.code == code)).first()


def create_camera(db: Session, data: dict[str, object]) -> Camera:
    camera = Camera(**data)
    db.add(camera)
    return camera


def update_camera(camera: Camera, data: dict[str, object]) -> Camera:
    for field, value in data.items():
        setattr(camera, field, value)
    return camera


def deactivate_camera(camera: Camera) -> Camera:
    camera.is_active = False
    return camera
