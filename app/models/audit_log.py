from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AuditLog(Base):
    __tablename__ = "tbllogsauditoria"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: Mapped[int] = mapped_column("IntLogAuditoriaid", primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        "IntUsuarioid",
        ForeignKey("tblusuarios.IntUsuarioid", name="fk_tbllogsauditoria_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column("StrAcao", String(100), nullable=False)
    entity_name: Mapped[str] = mapped_column("StrEntidade", String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column("IntEntidadeid", String(50), nullable=True)
    details: Mapped[dict | None] = mapped_column("StrDetalhes", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "DtdCriacao",
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User")


Index("ix_tbllogsauditoria_criacao", AuditLog.created_at)
Index("ix_tbllogsauditoria_entidade", AuditLog.entity_name)
