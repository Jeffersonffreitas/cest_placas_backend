from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, ORMBaseSchema


class VehicleBase(BaseSchema):
    student_id: int = Field(gt=0)
    plate: str = Field(min_length=1, max_length=10)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=50)
    brand_id: int | None = Field(default=None, gt=0)
    model_id: int | None = Field(default=None, gt=0)
    color_id: int | None = Field(default=None, gt=0)
    is_active: bool = True


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseSchema):
    student_id: int | None = Field(default=None, gt=0)
    plate: str | None = Field(default=None, min_length=1, max_length=10)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=50)
    brand_id: int | None = Field(default=None, gt=0)
    model_id: int | None = Field(default=None, gt=0)
    color_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class VehicleRead(ORMBaseSchema):
    id: int
    student_id: int
    plate: str
    brand: str | None
    model: str | None
    color: str | None
    brand_id: int | None
    model_id: int | None
    color_id: int | None
    brand_name: str | None
    model_name: str | None
    color_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
