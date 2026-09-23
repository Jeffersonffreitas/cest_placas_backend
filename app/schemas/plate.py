from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.access_event import AccessEventRead, AccessEventStatus
from app.schemas.common import BaseSchema
from app.schemas.person import PersonRead, PersonType
from app.schemas.student import StudentRead
from app.schemas.vehicle import VehicleRead


OperationalDecision = Literal[
    "ACESSO_LIBERADO",
    "VEICULO_NAO_CADASTRADO",
    "PESSOA_NAO_VINCULADA",
    "OCR_BAIXA_CONFIANCA",
    "PLACA_INVALIDA",
    "ERRO_OCR",
    "CADASTRO_INATIVO",
]


class ManualPlateReadRequest(BaseSchema):
    plate: str = Field(min_length=1, max_length=20)


class ManualPlateReadResponse(BaseSchema):
    success: Literal[True] = True
    message: str
    id: int
    access_event_id: int
    plate_read_id: int
    plate_input: str
    plate_normalized: str
    source: str
    confidence: float | None = None
    status: AccessEventStatus
    operational_decision: OperationalDecision
    access_event: AccessEventRead
    vehicle: VehicleRead | None
    person: PersonRead | None
    person_type: PersonType | None
    action: str | None
    origin: str | None
    student: StudentRead | None
    created_at: datetime


class ImagePlateReadResponse(ManualPlateReadResponse):
    image_path: str
