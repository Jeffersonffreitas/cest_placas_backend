import logging
from typing import NoReturn

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.integrations.institutional import (
    InstitutionalPerson,
    InstitutionalPersonProvider,
    InstitutionalProviderError,
    InstitutionalProviderUnavailableError,
    normalize_institutional_person_type,
    normalize_registration,
)
from app.models.course import Course
from app.models.person import Person
from app.repositories import coordinations as coordination_repository
from app.repositories import courses as course_repository
from app.repositories import people as person_repository
from app.schemas.institutional import (
    InstitutionalCoordinationRead,
    InstitutionalPersonRead,
)


logger = logging.getLogger(__name__)


def _provider_name(provider: InstitutionalPersonProvider) -> str:
    return provider.__class__.__name__


def _invalid_provider_response(
    provider: InstitutionalPersonProvider,
    registration: str,
    *,
    code: str = "institutional_provider_invalid_response",
) -> NoReturn:
    logger.warning(
        "Invalid institutional provider response: provider=%s registration=%s",
        _provider_name(provider),
        registration,
    )
    raise AppException(
        "The institutional provider returned invalid data.",
        status_code=502,
        code=code,
    )


def _find_source(
    registration: str,
    provider: InstitutionalPersonProvider,
) -> InstitutionalPerson | None:
    try:
        return provider.find_by_registration(registration)
    except InstitutionalProviderUnavailableError:
        logger.warning(
            "Institutional provider unavailable: provider=%s registration=%s",
            _provider_name(provider),
            registration,
        )
        raise AppException(
            "The institutional provider is temporarily unavailable.",
            status_code=503,
            code="institutional_provider_unavailable",
        ) from None
    except InstitutionalProviderError:
        logger.error(
            "Institutional provider failed: provider=%s registration=%s",
            _provider_name(provider),
            registration,
        )
        raise AppException(
            "The institutional provider could not complete the request.",
            status_code=502,
            code="institutional_provider_error",
        ) from None
    except Exception as exc:
        logger.error(
            "Unexpected institutional provider failure: provider=%s "
            "registration=%s exception=%s",
            _provider_name(provider),
            registration,
            exc.__class__.__name__,
        )
        raise AppException(
            "The institutional provider is temporarily unavailable.",
            status_code=503,
            code="institutional_provider_unavailable",
        ) from None


def _to_schema(
    person: InstitutionalPerson,
    provider: InstitutionalPersonProvider,
    expected_registration: str,
) -> InstitutionalPersonRead:
    if not isinstance(person, InstitutionalPerson):
        _invalid_provider_response(provider, expected_registration)
    if not isinstance(person.registration, str):
        _invalid_provider_response(provider, expected_registration)
    registration = normalize_registration(person.registration)
    if registration != expected_registration:
        _invalid_provider_response(provider, expected_registration)
    if not isinstance(person.person_type, str):
        _invalid_provider_response(
            provider,
            expected_registration,
            code="institutional_person_type_invalid",
        )
    try:
        person_type = normalize_institutional_person_type(person.person_type)
    except ValueError:
        _invalid_provider_response(
            provider,
            expected_registration,
            code="institutional_person_type_invalid",
        )
    if not isinstance(person.active, bool):
        _invalid_provider_response(provider, expected_registration)
    if person.course is not None and not hasattr(person.course, "name"):
        _invalid_provider_response(provider, expected_registration)
    if person.coordination is not None and not hasattr(person.coordination, "name"):
        _invalid_provider_response(provider, expected_registration)

    try:
        return InstitutionalPersonRead(
            registration=registration,
            full_name=person.full_name,
            person_type=person_type,
            email=person.email,
            phone=person.phone,
            active=person.active,
            course=(
                {"name": person.course.name, "code": person.course.code}
                if person.course is not None
                else None
            ),
            coordination=(
                {
                    "name": person.coordination.name,
                    "acronym": person.coordination.acronym,
                }
                if person.coordination is not None
                else None
            ),
        )
    except (AttributeError, TypeError, ValidationError):
        _invalid_provider_response(provider, expected_registration)


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
    person = _find_source(normalized_registration, provider)
    if person is None:
        raise AppException(
            "Institutional person was not found.",
            status_code=404,
            code="institutional_person_not_found",
        )
    resolved = _to_schema(person, provider, normalized_registration)
    if require_active and not resolved.active:
        raise AppException(
            "Institutional person is inactive.",
            status_code=409,
            code="institutional_person_inactive",
        )
    return resolved


def _sync_coordination(
    db: Session, coordination: InstitutionalCoordinationRead,
) -> int:
    row = coordination_repository.get_by_identity(
        db, acronym=coordination.acronym, name=coordination.name
    )
    if row is None:
        row = coordination_repository.create_coordination(
            db,
            {
                "name": coordination.name,
                "acronym": coordination.acronym,
                "is_active": True,
            },
        )
        db.flush()
    else:
        row.name = coordination.name
        if coordination.acronym is not None:
            row.acronym = coordination.acronym
        row.is_active = True
    return row.id


def _sync_course(db: Session, person: InstitutionalPersonRead) -> Course | None:
    if (
        person.person_type != "ALUNO"
        or person.course is None
        or person.coordination is None
    ):
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
        if person.course.code is not None:
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
    source = _find_source(normalized_registration, provider)
    if source is None:
        raise AppException(
            "Institutional person was not found.",
            status_code=404,
            code="institutional_person_not_found",
        )
    resolved = _to_schema(source, provider, normalized_registration)
    if not resolved.active:
        raise AppException(
            "Institutional person is inactive.",
            status_code=409,
            code="institutional_person_inactive",
        )
    try:
        person = _select_person_for_sync(db, resolved.registration)
        course = _sync_course(db, resolved)
        values: dict[str, object] = {
            "registration_number": resolved.registration,
            "full_name": resolved.full_name,
            "person_type": resolved.person_type,
            "is_active": resolved.active,
        }
        if resolved.email is not None:
            values["email"] = resolved.email
        if resolved.phone is not None:
            values["phone"] = resolved.phone
        if course is not None:
            values["course_id"] = course.id
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
