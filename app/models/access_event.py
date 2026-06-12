from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AccessEvent(Base):
    __tablename__ = "tbleventosacesso"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntEventoAcessoid", primary_key=True, autoincrement=True)
    plate_input: Mapped[str] = mapped_column("StrPlacaEntrada", String(20), nullable=False)
    plate_normalized: Mapped[str] = mapped_column("StrPlacaNormalizada", String(10), nullable=False)
    student_id: Mapped[int | None] = mapped_column(
        "IntAlunoid",
        ForeignKey("tblalunos.IntAlunoid", name="fk_tbleventosacesso_aluno", ondelete="SET NULL"),
        nullable=True,
    )
    vehicle_id: Mapped[int | None] = mapped_column(
        "IntVeiculoid",
        ForeignKey("tblveiculos.IntVeiculoid", name="fk_tbleventosacesso_veiculo", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        "StrOrigem",
        String(30),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    status: Mapped[str] = mapped_column("StrSituacao", String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "DtdCriacao",
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )

    student = relationship("Student", back_populates="access_events")
    vehicle = relationship("Vehicle", back_populates="access_events")


Index("ix_tbleventosacesso_placa_normalizada", AccessEvent.plate_normalized)
Index("ix_tbleventosacesso_origem", AccessEvent.source)
Index("ix_tbleventosacesso_situacao", AccessEvent.status)
Index("ix_tbleventosacesso_aluno", AccessEvent.student_id)
Index("ix_tbleventosacesso_veiculo", AccessEvent.vehicle_id)
Index("ix_tbleventosacesso_criacao", AccessEvent.created_at)
