from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.vehicle import Vehicle


def list_students(db: Session, *, skip: int = 0, limit: int = 100) -> list[Student]:
    statement = select(Student).order_by(Student.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_student(db: Session, student_id: int) -> Student | None:
    return db.get(Student, student_id)


def get_student_by_registration_number(
    db: Session,
    registration_number: str,
) -> Student | None:
    statement = select(Student).where(Student.registration_number == registration_number)
    return db.scalars(statement).first()


def get_student_by_email(db: Session, email: str) -> Student | None:
    statement = select(Student).where(Student.email == email)
    return db.scalars(statement).first()


def create_student(db: Session, data: dict[str, object]) -> Student:
    student = Student(**data)
    db.add(student)
    return student


def update_student(student: Student, data: dict[str, object]) -> Student:
    for field, value in data.items():
        setattr(student, field, value)
    return student


def delete_student(db: Session, student: Student) -> None:
    db.delete(student)


def count_student_vehicles(db: Session, student_id: int) -> int:
    statement = select(func.count()).select_from(Vehicle).where(Vehicle.student_id == student_id)
    return int(db.scalar(statement) or 0)
