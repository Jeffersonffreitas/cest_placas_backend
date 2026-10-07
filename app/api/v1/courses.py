from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.course import CourseRead
from app.services import courses as course_service


router = APIRouter(tags=["courses"])


@router.get("", response_model=list[CourseRead], summary="List courses")
def list_courses(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    active: Annotated[bool | None, Query()] = None,
    coordination_id: Annotated[int | None, Query(gt=0)] = None,
    name: Annotated[str | None, Query(min_length=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[CourseRead]:
    del admin_user
    rows = course_service.list_courses(
        db, is_active=active, coordination_id=coordination_id,
        name=name, skip=skip, limit=limit,
    )
    return [CourseRead.model_validate(row) for row in rows]
