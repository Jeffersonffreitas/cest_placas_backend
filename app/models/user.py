from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class User(Base):
    __tablename__ = "tblusuarios"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntUsuarioid", primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column("StrUsuario", String(100), nullable=False)
    full_name: Mapped[str | None] = mapped_column("StrNomeCompleto", String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column("StrSenhaHash", String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "IntAtivo",
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    is_superuser: Mapped[bool] = mapped_column(
        "IntSuperUsuario",
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
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


Index("ix_tblusuarios_usuario", User.username, unique=True)

