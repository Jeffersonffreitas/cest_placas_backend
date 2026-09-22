from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.access_event import AccessEventStatus
from app.schemas.common import BaseSchema
from app.schemas.student import StudentRead
from app.schemas.person import PersonRead
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
    id: int
    access_event_id: int
    plate_read_id: int
    plate_input: str
    plate_normalized: str
    source: str
    status: AccessEventStatus
    operational_decision: OperationalDecision
    vehicle: VehicleRead | None
    person: PersonRead | None
    student: StudentRead | None
    created_at: datetime


class ImagePlateReadResponse(ManualPlateReadResponse):
    image_path: str
    confidence: float | None
