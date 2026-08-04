from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.person import Person


def list_people(
    db: Session, *, person_type: str | None = None,
    registration_number: str | None = None, is_active: bool | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Person]:
    statement = select(Person)
    if person_type is not None:
        statement = statement.where(Person.person_type == person_type)
    if registration_number is not None:
        statement = statement.where(Person.registration_number == registration_number)
    if is_active is not None:
        statement = statement.where(Person.is_active.is_(is_active))
    statement = statement.order_by(Person.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_person(db: Session, person_id: int) -> Person | None:
    return db.get(Person, person_id)


def get_person_by_registration_number(
    db: Session, registration_number: str,
) -> Person | None:
    statement = (
        select(Person)
        .where(Person.registration_number == registration_number)
        .order_by(Person.is_active.desc(), Person.id.desc())
    )
    return db.scalars(statement).first()


def get_active_person_by_registration_number(
    db: Session, registration_number: str,
) -> Person | None:
    statement = select(Person).where(
        Person.registration_number == registration_number,
        Person.is_active.is_(True),
    )
    return db.scalars(statement).first()


def create_person(db: Session, data: dict[str, object]) -> Person:
    person = Person(**data)
    db.add(person)
    return person


def update_person(person: Person, data: dict[str, object]) -> Person:
    for field, value in data.items():
        setattr(person, field, value)
    return person


def deactivate_person(person: Person) -> Person:
    person.is_active = False
    return person
