from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Course(Base):
    __tablename__ = "tblcursos"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("intcursoid", primary_key=True, autoincrement=True)
    coordination_id: Mapped[int] = mapped_column(
        "intcoordenacaoid",
        ForeignKey(
            "tblcoordenacoes.intcoordenacaoid",
            name="fk_tblcursos_coordenacao",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column("strnome", String(255), nullable=False)
    code: Mapped[str | None] = mapped_column("strcodigo", String(100), nullable=True)
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

    coordination = relationship("Coordination", back_populates="courses")
    people = relationship("Person", back_populates="course")


Index("idx_tblcursos_intcoordenacaoid", Course.coordination_id)
Index("idx_tblcursos_strnome", Course.name)
Index("idx_tblcursos_strcodigo", Course.code)
Index("idx_tblcursos_bolativo", Course.is_active)
