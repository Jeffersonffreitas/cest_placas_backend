from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PlateRead(Base):
    __tablename__ = "plate_reads"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntPlateReadid", primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        "IntVehicleid",
        ForeignKey("vehicles.IntVehicleid", name="fk_plate_reads_vehicle_id_vehicles", ondelete="SET NULL"),
        nullable=True,
    )
    plate: Mapped[str] = mapped_column("StrPlate", String(10), nullable=False)
    source: Mapped[str] = mapped_column(
        "StrSource",
        String(30),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    confidence: Mapped[Decimal | None] = mapped_column("DecConfidence", Numeric(5, 2), nullable=True)
    image_path: Mapped[str | None] = mapped_column("StrImagePath", String(255), nullable=True)
    read_at: Mapped[datetime] = mapped_column("DtdReadAt", DateTime(), nullable=False)
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

    vehicle = relationship("Vehicle", back_populates="plate_reads")


Index("ix_plate_reads_plate", PlateRead.plate)
Index("ix_plate_reads_read_at", PlateRead.read_at)
