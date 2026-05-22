from datetime import datetime

from pydantic import Field

from app.schemas.access_event import AccessEventStatus
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
    status: AccessEventStatus
    vehicle: VehicleRead | None
    student: StudentRead | None
    created_at: datetime


class ImagePlateReadResponse(ManualPlateReadResponse):
    image_path: str
    confidence: float | None
