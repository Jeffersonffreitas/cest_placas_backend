from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.student import Student
from app.repositories import students as student_repository
from app.schemas.student import StudentCreate, StudentUpdate


def list_students(db: Session, *, skip: int = 0, limit: int = 100) -> list[Student]:
    return student_repository.list_students(db, skip=skip, limit=limit)


def get_student_or_404(db: Session, student_id: int) -> Student:
    student = student_repository.get_student(db, student_id)
    if student is None:
        raise AppException(
            "Student was not found.",
            status_code=404,
            code="student_not_found",
        )
    return student


def _ensure_unique_registration_number(
    db: Session,
    registration_number: str,
    *,
    current_student_id: int | None = None,
) -> None:
    student = student_repository.get_student_by_registration_number(db, registration_number)
    if student is not None and student.id != current_student_id:
        raise AppException(
            "Registration number already exists.",
            status_code=409,
            code="student_registration_number_conflict",
        )


def _ensure_unique_email(
    db: Session,
    email: str | None,
    *,
    current_student_id: int | None = None,
) -> None:
    if email is None:
        return

    student = student_repository.get_student_by_email(db, email)
    if student is not None and student.id != current_student_id:
        raise AppException(
            "Student email already exists.",
            status_code=409,
            code="student_email_conflict",
        )


def create_student(db: Session, payload: StudentCreate) -> Student:
    data = payload.model_dump()
    _ensure_unique_registration_number(db, str(data["registration_number"]))
    _ensure_unique_email(db, data.get("email") if isinstance(data.get("email"), str) else None)

    student = student_repository.create_student(db, data)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Student unique data already exists.",
            status_code=409,
            code="student_conflict",
        ) from None
    db.refresh(student)
    return student


def update_student(db: Session, student_id: int, payload: StudentUpdate) -> Student:
    student = get_student_or_404(db, student_id)
    data = payload.model_dump(exclude_unset=True)

    registration_number = data.get("registration_number")
    if isinstance(registration_number, str):
        _ensure_unique_registration_number(
            db,
            registration_number,
            current_student_id=student.id,
        )

    if "email" in data:
        email = data["email"]
        _ensure_unique_email(
            db,
            email if isinstance(email, str) else None,
            current_student_id=student.id,
        )

    student_repository.update_student(student, data)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Student unique data already exists.",
            status_code=409,
            code="student_conflict",
        ) from None
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: int) -> None:
    student = get_student_or_404(db, student_id)
    if student_repository.count_student_vehicles(db, student_id) > 0:
        raise AppException(
            "Student has linked vehicles and cannot be deleted.",
            status_code=409,
            code="student_has_vehicles",
        )

    student_repository.delete_student(db, student)
    db.commit()
