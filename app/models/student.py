from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Student(Base):
    __tablename__ = "tblalunos"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntAlunoid", primary_key=True, autoincrement=True)
    registration_number: Mapped[str] = mapped_column("StrMatricula", String(50), nullable=False)
    full_name: Mapped[str] = mapped_column("StrNomeCompleto", String(255), nullable=False)
    email: Mapped[str | None] = mapped_column("StrEmail", String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column("StrTelefone", String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "IntAtivo",
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
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

    vehicles = relationship("Vehicle", back_populates="student")
    access_events = relationship("AccessEvent", back_populates="student")


Index("ix_tblalunos_matricula", Student.registration_number, unique=True)
Index("ix_tblalunos_email", Student.email, unique=True)

