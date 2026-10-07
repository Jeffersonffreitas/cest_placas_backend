from typing import Literal

from app.schemas.common import BaseSchema
from app.schemas.person import PersonRead


class InstitutionalCoordinationRead(BaseSchema):
    name: str
    acronym: str | None = None


class InstitutionalCourseRead(BaseSchema):
    name: str
    code: str | None = None


class InstitutionalPersonRead(BaseSchema):
    registration: str
    full_name: str
    person_type: Literal["ALUNO", "FUNCIONARIO"]
    email: str | None
    active: bool
    course: InstitutionalCourseRead | None
    coordination: InstitutionalCoordinationRead | None


class InstitutionalPersonSyncRead(PersonRead):
    pass
