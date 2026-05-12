from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.plates import router as plates_router
from app.api.v1.students import router as students_router
from app.api.v1.vehicles import router as vehicles_router
from app.core.config import settings


api_router = APIRouter()
api_router.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth")
api_router.include_router(students_router, prefix=f"{settings.api_v1_prefix}/students")
api_router.include_router(vehicles_router, prefix=f"{settings.api_v1_prefix}/vehicles")
api_router.include_router(plates_router, prefix=f"{settings.api_v1_prefix}/plates")
api_router.include_router(health_router)
