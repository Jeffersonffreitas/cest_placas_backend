from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.student import Student
from app.models.person_vehicle import PersonVehicle


def list_students(db: Session, *, skip: int = 0, limit: int = 100) -> list[Person]:
    statement = (
        select(Person)
        .where(Person.person_type == "ALUNO")
        .order_by(Person.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_student(db: Session, student_id: int) -> Person | None:
    statement = select(Person).where(
        Person.id == student_id, Person.person_type == "ALUNO"
    )
    return db.scalars(statement).first()


def get_student_by_registration_number(
    db: Session,
    registration_number: str,
) -> Person | None:
    statement = (
        select(Person)
        .where(
            Person.person_type == "ALUNO",
            Person.registration_number == registration_number,
        )
        .order_by(Person.is_active.desc(), Person.id.desc())
    )
    return db.scalars(statement).first()


def get_active_student_by_registration_number(
    db: Session,
    registration_number: str,
) -> Person | None:
    statement = select(Person).where(
        Person.person_type == "ALUNO",
        Person.registration_number == registration_number,
        Person.is_active.is_(True),
    )
    return db.scalars(statement).first()


def get_student_by_email(db: Session, email: str) -> Person | None:
    statement = select(Person).where(
        Person.person_type == "ALUNO", Person.email == email
    )
    return db.scalars(statement).first()


def create_student(db: Session, data: dict[str, object]) -> Person:
    student = Person(person_type="ALUNO", **data)
    db.add(student)
    return student


def update_student(student: Person, data: dict[str, object]) -> Person:
    for field, value in data.items():
        setattr(student, field, value)
    return student


def delete_student(db: Session, student: Student) -> None:
    db.delete(student)


def deactivate_student(student: Person) -> Person:
    student.is_active = False
    return student


def count_student_vehicles(db: Session, student_id: int) -> int:
    statement = select(func.count()).select_from(PersonVehicle).where(
        PersonVehicle.person_id == student_id,
        PersonVehicle.is_active.is_(True),
    )
    return int(db.scalar(statement) or 0)


def get_legacy_student_by_registration_number(
    db: Session, registration_number: str,
) -> Student | None:
    return db.scalars(
        select(Student).where(Student.registration_number == registration_number)
    ).first()


def create_legacy_student(
    db: Session, data: dict[str, object], *, preferred_id: int,
) -> Student:
    legacy_id = preferred_id if db.get(Student, preferred_id) is None else None
    student = Student(id=legacy_id, **data)
    db.add(student)
    return student


def update_legacy_student(student: Student, data: dict[str, object]) -> Student:
    for field, value in data.items():
        setattr(student, field, value)
    return student


def deactivate_legacy_student(student: Student) -> Student:
    student.is_active = False
    return student
