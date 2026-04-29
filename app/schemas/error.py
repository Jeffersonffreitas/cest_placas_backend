from datetime import datetime
from typing import Any, Literal

from app.schemas.common import BaseSchema


class ErrorDetail(BaseSchema):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseSchema):
    success: Literal[False] = False
    error: ErrorDetail
    path: str
    timestamp: datetime

