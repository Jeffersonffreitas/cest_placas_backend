from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, ORMBaseSchema


class PersonVehicleCreate(BaseSchema):
    person_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)


class PersonVehicleUpdate(BaseSchema):
    is_active: bool | None = None


class PersonVehicleRead(ORMBaseSchema):
    id: int
    person_id: int
    vehicle_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PersonVehicleListItem(PersonVehicleRead):
    pass
