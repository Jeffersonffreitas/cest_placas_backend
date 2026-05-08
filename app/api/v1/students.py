from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdminUser
from app.db.deps import get_db
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate
from app.services import students as student_service


router = APIRouter(tags=["students"])


@router.post(
    "",
    response_model=StudentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create student",
)
def create_student(
    payload: StudentCreate,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> StudentRead:
    del admin_user
    return StudentRead.model_validate(student_service.create_student(db, payload))


@router.get(
    "",
    response_model=list[StudentRead],
    status_code=status.HTTP_200_OK,
    summary="List students",
)
def list_students(
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[StudentRead]:
    del admin_user
    students = student_service.list_students(db, skip=skip, limit=limit)
    return [StudentRead.model_validate(student) for student in students]


@router.get(
    "/{student_id}",
    response_model=StudentRead,
    status_code=status.HTTP_200_OK,
    summary="Get student by id",
)
def get_student(
    student_id: int,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> StudentRead:
    del admin_user
    return StudentRead.model_validate(student_service.get_student_or_404(db, student_id))


@router.put(
    "/{student_id}",
    response_model=StudentRead,
    status_code=status.HTTP_200_OK,
    summary="Update student",
)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> StudentRead:
    del admin_user
    return StudentRead.model_validate(student_service.update_student(db, student_id, payload))


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete student",
)
def delete_student(
    student_id: int,
    admin_user: CurrentAdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    del admin_user
    student_service.delete_student(db, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
