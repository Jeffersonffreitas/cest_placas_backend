from datetime import datetime
from typing import Literal

from app.schemas.common import ORMBaseSchema
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead


AccessEventStatus = Literal["matched", "not_found"]
AccessEventSource = Literal["manual", "upload"]


class AccessEventRead(ORMBaseSchema):
    id: int
    plate_input: str
    plate_normalized: str
    source: AccessEventSource
    status: AccessEventStatus
    vehicle: VehicleRead | None
    student: StudentRead | None
    created_at: datetime


class AccessEventSummaryPeriod(ORMBaseSchema):
    date_from: datetime | None = None
    date_to: datetime | None = None


class AccessEventSummaryRead(ORMBaseSchema):
    total_events: int
    total_matched: int
    total_not_found: int
    total_manual: int
    total_upload: int
    total_by_status: dict[str, int]
    total_by_source: dict[str, int]
    period: AccessEventSummaryPeriod | None = None
