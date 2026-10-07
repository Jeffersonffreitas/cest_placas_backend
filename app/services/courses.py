from sqlalchemy.orm import Session

from app.models.course import Course
from app.repositories import courses as course_repository


def list_courses(
    db: Session, *, is_active: bool | None = None,
    coordination_id: int | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Course]:
    normalized_name = name.strip() if name is not None else None
    return course_repository.list_courses(
        db, is_active=is_active, coordination_id=coordination_id,
        name=normalized_name, skip=skip, limit=limit,
    )
