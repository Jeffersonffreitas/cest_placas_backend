from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedModel


class Student(TimestampedModel, Base):
    __tablename__ = "students"
    __table_args__ = (
        Index("ix_students_registration_number", "registration_number", unique=True),
        Index("ix_students_email", "email", unique=True),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    registration_number: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    vehicles = relationship("Vehicle", back_populates="student")
    access_events = relationship("AccessEvent", back_populates="student")

