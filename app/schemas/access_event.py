from datetime import datetime
from typing import Literal

from app.schemas.common import ORMBaseSchema
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead


AccessEventStatus = Literal["matched", "not_found"]


class AccessEventRead(ORMBaseSchema):
    id: int
    plate_input: str
    plate_normalized: str
    source: str
    status: AccessEventStatus
    vehicle: VehicleRead | None
    student: StudentRead | None
    created_at: datetime
