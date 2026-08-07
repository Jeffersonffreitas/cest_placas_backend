from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PersonVehicle(Base):
    __tablename__ = "tblpessoaveiculo"
    __table_args__ = (
        UniqueConstraint(
            "numpessoaid", "numveiculoid", name="uq_tblpessoaveiculo_pessoa_veiculo"
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        "numpessoaveiculoid", primary_key=True, autoincrement=True
    )
    person_id: Mapped[int] = mapped_column(
        "numpessoaid",
        ForeignKey("tblpessoas.numpessoaid", name="fk_tblpessoaveiculo_pessoa", ondelete="RESTRICT"),
        nullable=False,
    )
    vehicle_id: Mapped[int] = mapped_column(
        "numveiculoid",
        ForeignKey("tblveiculos.numveiculoid", name="fk_tblpessoaveiculo_veiculo", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        "bolativo", Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        "dtacriacao", DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "dtaatualizacao", DateTime(), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    person = relationship("Person", back_populates="vehicle_links")
    vehicle = relationship("Vehicle", back_populates="person_links")


Index("idx_tblpessoaveiculo_numpessoaid", PersonVehicle.person_id)
Index("idx_tblpessoaveiculo_numveiculoid", PersonVehicle.vehicle_id)
Index("idx_tblpessoaveiculo_bolativo", PersonVehicle.is_active)
