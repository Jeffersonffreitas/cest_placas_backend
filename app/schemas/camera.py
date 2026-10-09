from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, ORMBaseSchema


class CameraCreate(BaseSchema):
    access_point_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class CameraUpdate(BaseSchema):
    access_point_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class CameraRead(ORMBaseSchema):
    id: int
    access_point_id: int
    name: str
    code: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CameraSummary(ORMBaseSchema):
    id: int
    name: str
