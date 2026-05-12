from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead


class ManualPlateReadRequest(BaseSchema):
    plate: str = Field(min_length=1, max_length=20)


class ManualPlateReadResponse(BaseSchema):
    id: int
    plate_input: str
    plate_normalized: str
    source: str
    status: Literal["matched", "not_found"]
    vehicle: VehicleRead | None
    student: StudentRead | None
    created_at: datetime
