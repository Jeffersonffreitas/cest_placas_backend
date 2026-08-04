from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.person import Person
from app.repositories import domains as domain_repository
from app.repositories import people as person_repository
from app.schemas.person import PersonCreate, PersonUpdate


def list_people(
    db: Session, *, person_type: str | None = None,
    registration_number: str | None = None, is_active: bool | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Person]:
    normalized_type = person_type.strip().upper() if person_type is not None else None
    normalized_registration = (
        registration_number.strip() if registration_number is not None else None
    )
    return person_repository.list_people(
        db, person_type=normalized_type, registration_number=normalized_registration,
        is_active=is_active, skip=skip, limit=limit,
    )


def get_person_or_404(db: Session, person_id: int) -> Person:
    person = person_repository.get_person(db, person_id)
    if person is None:
        raise AppException("Person was not found.", status_code=404, code="person_not_found")
    return person


def get_person_by_registration_number_or_404(
    db: Session, registration_number: str,
) -> Person:
    person = person_repository.get_person_by_registration_number(
        db, registration_number.strip()
    )
    if person is None:
        raise AppException("Person was not found.", status_code=404, code="person_not_found")
    return person


def _validate_course(db: Session, course_id: int | None) -> None:
    if course_id is None:
        return
    domain = domain_repository.get_domain(db, course_id)
    if domain is None or not domain.is_active:
        raise AppException(
            "course_id must reference an active domain.",
            status_code=422,
            code="invalid_course_id",
        )


def _ensure_unique_active_registration(
    db: Session, registration_number: str, *, is_active: bool,
    current_person_id: int | None = None,
) -> None:
    if not is_active:
        return
    person = person_repository.get_active_person_by_registration_number(
        db, registration_number
    )
    if person is not None and person.id != current_person_id:
        raise AppException(
            "An active person with this registration number already exists.",
            status_code=409,
            code="person_registration_number_conflict",
        )


def _commit(db: Session, person: Person) -> Person:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Person data conflicts with an existing record.",
            status_code=409,
            code="person_conflict",
        ) from None
    db.refresh(person)
    return person


def create_person(db: Session, payload: PersonCreate) -> Person:
    data = payload.model_dump()
    registration_number = str(data["registration_number"])
    _validate_course(db, data.get("course_id") if isinstance(data.get("course_id"), int) else None)
    _ensure_unique_active_registration(
        db, registration_number, is_active=bool(data["is_active"])
    )
    return _commit(db, person_repository.create_person(db, data))


def update_person(db: Session, person_id: int, payload: PersonUpdate) -> Person:
    person = get_person_or_404(db, person_id)
    data = payload.model_dump(exclude_unset=True)
    course_id = data.get("course_id", person.course_id)
    _validate_course(db, course_id if isinstance(course_id, int) else None)
    registration_number = str(data.get("registration_number", person.registration_number))
    is_active = bool(data.get("is_active", person.is_active))
    _ensure_unique_active_registration(
        db, registration_number, is_active=is_active, current_person_id=person.id
    )
    person_repository.update_person(person, data)
    return _commit(db, person)


def delete_person(db: Session, person_id: int) -> None:
    person = get_person_or_404(db, person_id)
    person_repository.deactivate_person(person)
    db.commit()
