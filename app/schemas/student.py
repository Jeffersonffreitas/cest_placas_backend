from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, ORMBaseSchema


class StudentBase(BaseSchema):
    registration_number: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool = True

    @field_validator("email", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseSchema):
    registration_number: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

    @field_validator("email", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class StudentRead(ORMBaseSchema):
    id: int
    registration_number: str
    full_name: str
    email: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
