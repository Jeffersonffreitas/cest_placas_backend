from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedModel


class PlateRead(TimestampedModel, Base):
    __tablename__ = "plate_reads"
    __table_args__ = (
        Index("ix_plate_reads_plate", "plate"),
        Index("ix_plate_reads_read_at", "read_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )
    plate: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual", server_default="manual")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)

    vehicle = relationship("Vehicle", back_populates="plate_reads")
