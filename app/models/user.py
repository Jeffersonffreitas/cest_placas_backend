from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class User(Base):
    __tablename__ = "tblusuarios"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("numusuarioid", primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column("strusuario", String(100), nullable=False)
    full_name: Mapped[str | None] = mapped_column("strnomecompleto", String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column("strsenhahash", String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "bolativo",
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    is_superuser: Mapped[bool] = mapped_column(
        "bolsuperusuario",
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
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


Index("ix_tblusuarios_usuario", User.username, unique=True)

