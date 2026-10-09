from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Camera(Base):
    __tablename__ = "tblcameras"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("intcameraid", primary_key=True, autoincrement=True)
    access_point_id: Mapped[int] = mapped_column(
        "intpontoacessoid",
        ForeignKey(
            "tblpontosacesso.intpontoacessoid",
            name="fk_tblcameras_pontoacesso",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column("strnome", String(255), nullable=False)
    code: Mapped[str] = mapped_column("strcodigo", String(100), nullable=False)
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

    access_point = relationship("AccessPoint", back_populates="cameras")
    plate_reads = relationship("PlateRead", back_populates="camera")


Index("idx_tblcameras_intpontoacessoid", Camera.access_point_id)
Index("uq_tblcameras_strcodigo", Camera.code, unique=True)
Index("idx_tblcameras_strnome", Camera.name)
Index("idx_tblcameras_bolativo", Camera.is_active)
