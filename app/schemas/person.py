from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, ORMBaseSchema


PersonType = Literal["ALUNO", "FUNCIONARIO"]


class PersonBase(BaseSchema):
    person_type: PersonType
    registration_number: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    course_id: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @field_validator("person_type", mode="before")
    @classmethod
    def normalize_person_type(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("email", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseSchema):
    person_type: PersonType | None = None
    registration_number: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    course_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("person_type", mode="before")
    @classmethod
    def normalize_person_type(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("email", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class PersonRead(ORMBaseSchema):
    id: int
    person_type: PersonType
    registration_number: str
    full_name: str
    email: str | None
    phone: str | None
    course_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PersonListItem(PersonRead):
    pass
