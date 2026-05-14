from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AccessEvent(Base):
    __tablename__ = "access_events"
    __table_args__ = (
        Index("ix_access_events_plate_normalized", "plate_normalized"),
        Index("ix_access_events_status", "status"),
        Index("ix_access_events_student_id", "student_id"),
        Index("ix_access_events_vehicle_id", "vehicle_id"),
        Index("ix_access_events_created_at", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plate_input: Mapped[str] = mapped_column(String(20), nullable=False)
    plate_normalized: Mapped[str] = mapped_column(String(10), nullable=False)
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
    )
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual", server_default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )

    student = relationship("Student", back_populates="access_events")
    vehicle = relationship("Vehicle", back_populates="access_events")
