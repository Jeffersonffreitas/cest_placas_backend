from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedModel


class AccessEvent(TimestampedModel, Base):
    __tablename__ = "access_events"
    __table_args__ = (
        Index("ix_access_events_event_at", "event_at"),
        Index("ix_access_events_plate", "plate"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
    )
    plate_read_id: Mapped[int | None] = mapped_column(
        ForeignKey("plate_reads.id", ondelete="SET NULL"),
        nullable=True,
    )
    plate: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)

    vehicle = relationship("Vehicle", back_populates="access_events")
    student = relationship("Student", back_populates="access_events")
    plate_read = relationship("PlateRead", back_populates="access_events")
