from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Computed, DateTime, ForeignKey, Index, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Person(Base):
    __tablename__ = "tblpessoas"
    __table_args__ = (
        CheckConstraint(
            "strtipopessoa IN ('ALUNO', 'FUNCIONARIO')",
            name="ck_tblpessoas_tipopessoa",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column("numpessoaid", primary_key=True, autoincrement=True)
    person_type: Mapped[str] = mapped_column("strtipopessoa", String(20), nullable=False)
    registration_number: Mapped[str] = mapped_column(
        "strmatricula", String(50), nullable=False
    )
    full_name: Mapped[str] = mapped_column("strnomecompleto", String(255), nullable=False)
    email: Mapped[str | None] = mapped_column("stremail", String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column("strtelefone", String(20), nullable=True)
    course_id: Mapped[int | None] = mapped_column(
        "numcursoid",
        ForeignKey("tbldominios.numdominioid", name="fk_tblpessoas_curso", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        "bolativo", Boolean, nullable=False, default=True, server_default="1"
    )
    active_registration_number: Mapped[str | None] = mapped_column(
        "strmatriculaativa",
        String(50),
        Computed("CASE WHEN bolativo = 1 THEN strmatricula ELSE NULL END", persisted=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "dtacriacao", DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "dtaatualizacao", DateTime(), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    course = relationship("Domain", foreign_keys=[course_id])
    vehicle_links = relationship("PersonVehicle", back_populates="person")


Index("idx_tblpessoas_strtipopessoa", Person.person_type)
Index("idx_tblpessoas_strmatricula", Person.registration_number)
Index("idx_tblpessoas_bolativo", Person.is_active)
Index("idx_tblpessoas_numcursoid", Person.course_id)
Index(
    "uq_tblpessoas_strmatriculaativa", Person.active_registration_number, unique=True
)
