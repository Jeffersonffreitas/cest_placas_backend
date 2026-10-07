from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course


def list_courses(
    db: Session, *, is_active: bool | None = None,
    coordination_id: int | None = None, name: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Course]:
    statement = select(Course).options(selectinload(Course.coordination))
    if is_active is not None:
        statement = statement.where(Course.is_active.is_(is_active))
    if coordination_id is not None:
        statement = statement.where(Course.coordination_id == coordination_id)
    if name is not None:
        statement = statement.where(func.lower(Course.name).like(f"%{name.lower()}%"))
    statement = statement.order_by(Course.name, Course.id)
    return list(db.scalars(statement.offset(skip).limit(limit)).all())


def get_course(db: Session, course_id: int) -> Course | None:
    return db.get(Course, course_id)


def get_by_identity(
    db: Session, *, code: str | None, name: str, coordination_id: int,
) -> Course | None:
    if code is not None:
        match = db.scalar(
            select(Course)
            .where(
                Course.coordination_id == coordination_id,
                func.lower(Course.code) == code.lower(),
            )
            .order_by(Course.id)
        )
        if match is not None:
            return match
    return db.scalar(
        select(Course)
        .where(
            Course.coordination_id == coordination_id,
            func.lower(Course.name) == name.lower(),
        )
        .order_by(Course.id)
    )


def create_course(db: Session, data: dict[str, object]) -> Course:
    course = Course(**data)
    db.add(course)
    return course
