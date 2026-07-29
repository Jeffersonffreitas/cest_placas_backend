from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, ORMBaseSchema


class DomainBase(BaseSchema):
    type: str = Field(min_length=1, max_length=50)
    code: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    parent_id: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @field_validator("type", "name")
    @classmethod
    def reject_blank_required_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("code")
    @classmethod
    def normalize_blank_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseSchema):
    type: str | None = Field(default=None, min_length=1, max_length=50)
    code: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("type", "name")
    @classmethod
    def reject_blank_required_fields(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("code")
    @classmethod
    def normalize_blank_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class DomainRead(ORMBaseSchema):
    id: int
    type: str
    code: str | None
    name: str
    parent_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
