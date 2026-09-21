from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, ORMBaseSchema
from app.schemas.person import PersonRead
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead


AccessEventStatus = Literal[
    "ACESSO_LIBERADO",
    "VEICULO_NAO_CADASTRADO",
    "PESSOA_NAO_VINCULADA",
    "OCR_BAIXA_CONFIANCA",
    "PLACA_INVALIDA",
    "matched",
    "not_found",
]
AccessEventSource = Literal["manual", "upload"]


class AccessEventCreate(BaseSchema):
    plate: str = Field(min_length=1, max_length=20)
    action_id: int | None = Field(default=None, gt=0)
    origin_id: int | None = Field(default=None, gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    person_id: int | None = Field(default=None, gt=0)
    plate_read_id: int | None = Field(default=None, gt=0)
    origin: str = Field(default="manual", min_length=1, max_length=30)
    source: str | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("origin", "source")
    @classmethod
    def normalize_origin(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class AccessEventRead(ORMBaseSchema):
    id: int
    vehicle_id: int | None
    person_id: int | None
    plate_read_id: int | None
    action_id: int | None
    origin_id: int | None
    status: AccessEventStatus
    plate_input: str
    plate_normalized: str
    origin: str
    source: str
    created_at: datetime
    vehicle: VehicleRead | None
    person: PersonRead | None
    student: StudentRead | None


class AccessEventListItem(AccessEventRead):
    pass


class AccessEventSummaryPeriod(ORMBaseSchema):
    date_from: datetime | None = None
    date_to: datetime | None = None


class AccessEventSummary(ORMBaseSchema):
    total: int
    by_status: dict[str, int]
    by_origin: dict[str, int]
    by_action: dict[str, int]
    by_person_type: dict[str, int]
    period: AccessEventSummaryPeriod | None = None
    total_events: int
    total_matched: int
    total_not_found: int
    total_manual: int
    total_upload: int
    total_by_status: dict[str, int]
    total_by_source: dict[str, int]


AccessEventSummaryRead = AccessEventSummary
