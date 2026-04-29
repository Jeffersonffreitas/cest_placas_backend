from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedModel


class Vehicle(TimestampedModel, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        Index("ix_vehicles_plate", "plate", unique=True),
        Index("ix_vehicles_student_id", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    plate: Mapped[str] = mapped_column(String(10), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    student = relationship("Student", back_populates="vehicles")
    plate_reads = relationship("PlateRead", back_populates="vehicle")
    access_events = relationship("AccessEvent", back_populates="vehicle")

