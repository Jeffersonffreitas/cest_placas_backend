"""Database models package.

Importing this package registers every SQLAlchemy model in the shared metadata.
"""

from app.db.base_class import Base
from app.models.access_event import AccessEvent
from app.models.audit_log import AuditLog
from app.models.domain import Domain
from app.models.plate_read import PlateRead
from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.student import Student
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "Base", "User", "Student", "Vehicle", "PlateRead", "AccessEvent",
    "AuditLog", "Domain", "Person", "PersonVehicle",
]
