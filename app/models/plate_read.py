from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PlateRead(Base):
    __tablename__ = "tblleiturasplacas"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntLeituraPlacaid", primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        "IntVeiculoid",
        ForeignKey("tblveiculos.IntVeiculoid", name="fk_tblleiturasplacas_veiculo", ondelete="SET NULL"),
        nullable=True,
    )
    plate: Mapped[str] = mapped_column("StrPlaca", String(10), nullable=False)
    source: Mapped[str] = mapped_column(
        "StrOrigem",
        String(30),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    confidence: Mapped[Decimal | None] = mapped_column("DecConfianca", Numeric(5, 2), nullable=True)
    image_path: Mapped[str | None] = mapped_column("StrCaminhoImagem", String(255), nullable=True)
    read_at: Mapped[datetime] = mapped_column("DtdLeitura", DateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "DtdCriacao",
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        "DtdAtualizacao",
        DateTime(),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    vehicle = relationship("Vehicle", back_populates="plate_reads")


Index("ix_tblleiturasplacas_placa", PlateRead.plate)
Index("ix_tblleiturasplacas_leitura", PlateRead.read_at)
