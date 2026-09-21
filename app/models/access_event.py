from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AccessEvent(Base):
    __tablename__ = "tbleventosacesso"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("inteventoacessoid", primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        "intveiculoid",
        ForeignKey("tblveiculos.intveiculoid", name="fk_tbleventosacesso_veiculo", ondelete="SET NULL"),
        nullable=True,
    )
    person_id: Mapped[int | None] = mapped_column(
        "intpessoaid",
        ForeignKey("tblpessoas.intpessoaid", name="fk_tbleventosacesso_pessoa", ondelete="SET NULL"),
        nullable=True,
    )
    plate_read_id: Mapped[int | None] = mapped_column(
        "intleituraplacaid",
        ForeignKey(
            "tblleiturasplacas.intleituraplacaid",
            name="fk_tbleventosacesso_leituraplaca",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    action_id: Mapped[int | None] = mapped_column(
        "intacaoid",
        ForeignKey("tbldominios.intdominioid", name="fk_tbleventosacesso_acao", ondelete="RESTRICT"),
        nullable=True,
    )
    origin_id: Mapped[int | None] = mapped_column(
        "intorigemid",
        ForeignKey("tbldominios.intdominioid", name="fk_tbleventosacesso_origem", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column("strsituacao", String(30), nullable=False)
    plate_input: Mapped[str] = mapped_column("strplacaentrada", String(20), nullable=False)
    plate_normalized: Mapped[str] = mapped_column("strplacanormalizada", String(10), nullable=False)
    origin: Mapped[str] = mapped_column(
        "strorigem", String(30), nullable=False, default="manual", server_default="manual"
    )
    created_at: Mapped[datetime] = mapped_column(
        "dtacriacao", DateTime(), nullable=False, server_default=func.now()
    )

    vehicle = relationship("Vehicle", back_populates="access_events")
    person = relationship("Person", back_populates="access_events")
    plate_read = relationship("PlateRead", back_populates="access_events")
    action = relationship("Domain", foreign_keys=[action_id])
    origin_domain = relationship("Domain", foreign_keys=[origin_id])

    @property
    def source(self) -> str:
        """Compatibility alias for the legacy public API."""
        return self.origin

    @source.setter
    def source(self, value: str) -> None:
        self.origin = value

    @property
    def student_id(self) -> int | None:
        """Legacy API field without a dependency on tblalunos."""
        if self.person is not None and self.person.person_type == "ALUNO":
            return self.person_id
        return None

    @student_id.setter
    def student_id(self, value: int | None) -> None:
        self.person_id = value

    @property
    def student(self):
        """Legacy response field backed by the resolved ALUNO person."""
        if self.person is not None and self.person.person_type == "ALUNO":
            return self.person
        return None


Index("ix_tbleventosacesso_placa_normalizada", AccessEvent.plate_normalized)
Index("ix_tbleventosacesso_origem", AccessEvent.origin)
Index("ix_tbleventosacesso_situacao", AccessEvent.status)
Index("ix_tbleventosacesso_veiculo", AccessEvent.vehicle_id)
Index("ix_tbleventosacesso_pessoa", AccessEvent.person_id)
Index("ix_tbleventosacesso_leituraplaca", AccessEvent.plate_read_id)
Index("ix_tbleventosacesso_acao", AccessEvent.action_id)
Index("ix_tbleventosacesso_origem_id", AccessEvent.origin_id)
Index("ix_tbleventosacesso_criacao", AccessEvent.created_at)
