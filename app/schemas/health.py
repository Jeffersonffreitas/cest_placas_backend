from app.schemas.common import BaseSchema


class HealthResponse(BaseSchema):
    status: str
    app_name: str
    version: str
    environment: str

