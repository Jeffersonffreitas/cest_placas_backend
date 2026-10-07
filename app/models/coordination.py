from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Coordination(Base):
    __tablename__ = "tblcoordenacoes"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column(
        "intcoordenacaoid", primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column("strnome", String(255), nullable=False)
    acronym: Mapped[str | None] = mapped_column("strsigla", String(50), nullable=True)
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

    courses = relationship("Course", back_populates="coordination")


Index("idx_tblcoordenacoes_strnome", Coordination.name)
Index("idx_tblcoordenacoes_strsigla", Coordination.acronym)
Index("idx_tblcoordenacoes_bolativo", Coordination.is_active)
