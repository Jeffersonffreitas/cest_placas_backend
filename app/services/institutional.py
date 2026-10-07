from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.integrations.institutional import (
    InstitutionalCoordination,
    InstitutionalPerson,
    InstitutionalPersonProvider,
    normalize_registration,
)
from app.models.course import Course
from app.models.person import Person
from app.repositories import coordinations as coordination_repository
from app.repositories import courses as course_repository
from app.repositories import people as person_repository
from app.schemas.institutional import InstitutionalPersonRead


def _to_schema(person: InstitutionalPerson) -> InstitutionalPersonRead:
    return InstitutionalPersonRead(
        registration=normalize_registration(person.registration),
        full_name=person.full_name,
        person_type=person.person_type,
        email=person.email,
        active=person.active,
        course=(
            {"name": person.course.name, "code": person.course.code}
            if person.course is not None
            else None
        ),
        coordination=(
            {"name": person.coordination.name, "acronym": person.coordination.acronym}
            if person.coordination is not None
            else None
        ),
    )


def resolve_institutional_person(
    registration: str,
    provider: InstitutionalPersonProvider,
    *,
    require_active: bool = False,
) -> InstitutionalPersonRead:
    normalized_registration = normalize_registration(registration)
    if not normalized_registration:
        raise AppException(
            "Institutional registration is required.",
            status_code=422,
            code="institutional_registration_required",
        )
    person = provider.find_by_registration(normalized_registration)
    if person is None:
        raise AppException(
            "Institutional person was not found.",
            status_code=404,
            code="institutional_person_not_found",
        )
    if require_active and not person.active:
        raise AppException(
            "Institutional person is inactive.",
            status_code=409,
            code="institutional_person_inactive",
        )
    return _to_schema(person)


def _sync_coordination(
    db: Session, coordination: InstitutionalCoordination | None,
) -> int:
    data = coordination or InstitutionalCoordination(
        name="Coordenação não informada", acronym="NAO_INFORMADA"
    )
    row = coordination_repository.get_by_identity(
        db, acronym=data.acronym, name=data.name
    )
    if row is None:
        row = coordination_repository.create_coordination(
            db,
            {"name": data.name, "acronym": data.acronym, "is_active": True},
        )
        db.flush()
    else:
        row.name = data.name
        row.acronym = data.acronym
        row.is_active = True
    return row.id


def _sync_course(db: Session, person: InstitutionalPerson) -> Course | None:
    if person.person_type != "ALUNO" or person.course is None:
        return None
    coordination_id = _sync_coordination(db, person.coordination)
    course = course_repository.get_by_identity(
        db,
        code=person.course.code,
        name=person.course.name,
        coordination_id=coordination_id,
    )
    if course is None:
        course = course_repository.create_course(
            db,
            {
                "coordination_id": coordination_id,
                "name": person.course.name,
                "code": person.course.code,
                "is_active": True,
            },
        )
        db.flush()
    else:
        course.name = person.course.name
        course.code = person.course.code
        course.is_active = True
    return course


def _select_person_for_sync(db: Session, registration: str) -> Person | None:
    matches = person_repository.list_people_by_registration_number(db, registration)
    institutional_matches = [
        person for person in matches if person.person_type in {"ALUNO", "FUNCIONARIO"}
    ]
    if len(institutional_matches) > 1:
        raise AppException(
            "Multiple local institutional people use this registration.",
            status_code=409,
            code="institutional_registration_conflict",
        )
    if institutional_matches:
        return institutional_matches[0]
    if any(person.person_type == "VISITANTE" for person in matches):
        raise AppException(
            "A visitor with this registration cannot be changed automatically.",
            status_code=409,
            code="institutional_visitor_conflict",
        )
    return None


def sync_institutional_person(
    db: Session,
    registration: str,
    provider: InstitutionalPersonProvider,
) -> Person:
    normalized_registration = normalize_registration(registration)
    if not normalized_registration:
        raise AppException(
            "Institutional registration is required.",
            status_code=422,
            code="institutional_registration_required",
        )
    source = provider.find_by_registration(normalized_registration)
    if source is None:
        raise AppException(
            "Institutional person was not found.",
            status_code=404,
            code="institutional_person_not_found",
        )
    if not source.active:
        raise AppException(
            "Institutional person is inactive.",
            status_code=409,
            code="institutional_person_inactive",
        )
    resolved = _to_schema(source)

    try:
        course = _sync_course(db, source)
        person = _select_person_for_sync(db, resolved.registration)
        values: dict[str, object] = {
            "registration_number": resolved.registration,
            "full_name": resolved.full_name,
            "person_type": resolved.person_type,
            "email": resolved.email,
            "is_active": resolved.active,
            "course_id": course.id if course is not None else None,
        }
        if person is None:
            person = person_repository.create_person(db, values)
        else:
            person_repository.update_person(person, values)
        db.commit()
    except AppException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise AppException(
            "Institutional person conflicts with local data.",
            status_code=409,
            code="institutional_sync_conflict",
        ) from None
    db.refresh(person)
    return person
