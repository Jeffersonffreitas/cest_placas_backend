from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AccessPoint(Base):
    __tablename__ = "tblpontosacesso"
    __table_args__ = (
        CheckConstraint(
            "strsentido IN ('ENTRADA', 'SAIDA', 'MISTO')",
            name="sentido",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(
        "intpontoacessoid", primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column("strnome", String(255), nullable=False)
    code: Mapped[str | None] = mapped_column("strcodigo", String(100), nullable=True)
    direction: Mapped[str] = mapped_column("strsentido", String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(
        "strdescricao", String(500), nullable=True
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

    cameras = relationship("Camera", back_populates="access_point")
    access_events = relationship("AccessEvent", back_populates="access_point")


Index("idx_tblpontosacesso_strnome", AccessPoint.name)
Index("idx_tblpontosacesso_strsentido", AccessPoint.direction)
Index("idx_tblpontosacesso_bolativo", AccessPoint.is_active)
