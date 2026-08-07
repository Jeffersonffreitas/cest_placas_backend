from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Vehicle(Base):
    __tablename__ = "tblveiculos"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("numveiculoid", primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        "numalunoid",
        ForeignKey("tblalunos.numalunoid", name="fk_tblveiculos_aluno", ondelete="RESTRICT"),
        nullable=False,
    )
    plate: Mapped[str] = mapped_column("strplaca", String(10), nullable=False)
    brand: Mapped[str | None] = mapped_column("strmarca", String(100), nullable=True)
    model: Mapped[str | None] = mapped_column("strmodelo", String(100), nullable=True)
    color: Mapped[str | None] = mapped_column("strcor", String(50), nullable=True)
    brand_id: Mapped[int | None] = mapped_column(
        "nummarcaid",
        ForeignKey("tbldominios.numdominioid", name="fk_tblveiculos_marca", ondelete="RESTRICT"),
        nullable=True,
    )
    model_id: Mapped[int | None] = mapped_column(
        "nummodeloid",
        ForeignKey("tbldominios.numdominioid", name="fk_tblveiculos_modelo", ondelete="RESTRICT"),
        nullable=True,
    )
    color_id: Mapped[int | None] = mapped_column(
        "numcorid",
        ForeignKey("tbldominios.numdominioid", name="fk_tblveiculos_cor", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        "bolativo",
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        "dtacriacao",
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        "dtaatualizacao",
        DateTime(),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    student = relationship("Student", back_populates="vehicles")
    plate_reads = relationship("PlateRead", back_populates="vehicle")
    access_events = relationship("AccessEvent", back_populates="vehicle")
    brand_domain = relationship("Domain", foreign_keys=[brand_id])
    model_domain = relationship("Domain", foreign_keys=[model_id])
    color_domain = relationship("Domain", foreign_keys=[color_id])
    person_links = relationship("PersonVehicle", back_populates="vehicle")

    @property
    def brand_name(self) -> str | None:
        return self.brand_domain.name if self.brand_domain is not None else self.brand

    @property
    def model_name(self) -> str | None:
        return self.model_domain.name if self.model_domain is not None else self.model

    @property
    def color_name(self) -> str | None:
        return self.color_domain.name if self.color_domain is not None else self.color


Index("ix_tblveiculos_placa", Vehicle.plate, unique=True)
Index("ix_tblveiculos_aluno", Vehicle.student_id)
Index("idx_tblveiculos_nummarcaid", Vehicle.brand_id)
Index("idx_tblveiculos_nummodeloid", Vehicle.model_id)
Index("idx_tblveiculos_numcorid", Vehicle.color_id)

