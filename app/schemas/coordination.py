from datetime import datetime

from app.schemas.common import ORMBaseSchema


class CoordinationRead(ORMBaseSchema):
    id: int
    name: str
    acronym: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
