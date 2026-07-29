from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Domain(Base):
    __tablename__ = "tbldominios"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("numdominioid", primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column("strtipo", String(50), nullable=False)
    code: Mapped[str | None] = mapped_column("strcodigo", String(100), nullable=True)
    name: Mapped[str] = mapped_column("strnome", String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        "numdominiopaiid",
        ForeignKey("tbldominios.numdominioid", name="fk_tbldominios_pai", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        "bolativo", Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        "dtacriacao", DateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "dtaatualizacao", DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped["Domain | None"] = relationship(
        "Domain", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Domain"]] = relationship("Domain", back_populates="parent")


Index("ix_tbldominios_tipo", Domain.type)
Index("ix_tbldominios_ativo", Domain.is_active)
Index("ix_tbldominios_pai", Domain.parent_id)
