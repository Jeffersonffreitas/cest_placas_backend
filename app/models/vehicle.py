from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntVehicleid", primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        "IntStudentid",
        ForeignKey("students.IntStudentid", name="fk_vehicles_student_id_students", ondelete="RESTRICT"),
        nullable=False,
    )
    plate: Mapped[str] = mapped_column("StrPlate", String(10), nullable=False)
    brand: Mapped[str | None] = mapped_column("StrBrand", String(100), nullable=True)
    model: Mapped[str | None] = mapped_column("StrModel", String(100), nullable=True)
    color: Mapped[str | None] = mapped_column("StrColor", String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "IntIsActive",
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        "DtdCreatedAt",
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        "DtdUpdatedAt",
        DateTime(),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    student = relationship("Student", back_populates="vehicles")
    plate_reads = relationship("PlateRead", back_populates="vehicle")
    access_events = relationship("AccessEvent", back_populates="vehicle")


Index("ix_vehicles_plate", Vehicle.plate, unique=True)
Index("ix_vehicles_student_id", Vehicle.student_id)

