from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema
from app.schemas.person import PersonRead


class InstitutionalCoordinationRead(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    acronym: str | None = Field(default=None, max_length=50)

    @field_validator("acronym", mode="before")
    @classmethod
    def empty_acronym_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class InstitutionalCourseRead(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=100)

    @field_validator("code", mode="before")
    @classmethod
    def empty_code_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class InstitutionalPersonRead(BaseSchema):
    registration: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    person_type: Literal["ALUNO", "FUNCIONARIO"]
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    active: bool
    course: InstitutionalCourseRead | None
    coordination: InstitutionalCoordinationRead | None

    @field_validator("email", "phone", mode="before")
    @classmethod
    def empty_optional_text_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class InstitutionalPersonSyncRead(PersonRead):
    pass
