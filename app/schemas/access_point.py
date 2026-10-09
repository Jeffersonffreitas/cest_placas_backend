from datetime import datetime

from pydantic import Field

from app.schemas.access_context import AccessPointDirection
from app.schemas.common import BaseSchema, ORMBaseSchema


class AccessPointCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=100)
    direction: AccessPointDirection
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class AccessPointUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=100)
    direction: AccessPointDirection | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class AccessPointRead(ORMBaseSchema):
    id: int
    name: str
    code: str | None
    direction: AccessPointDirection
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccessPointSummary(ORMBaseSchema):
    id: int
    name: str
    direction: AccessPointDirection
