from datetime import datetime

from app.schemas.common import ORMBaseSchema
from app.schemas.coordination import CoordinationRead


class CourseRead(ORMBaseSchema):
    id: int
    coordination_id: int
    name: str
    code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    coordination: CoordinationRead
