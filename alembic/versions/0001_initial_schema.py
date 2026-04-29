"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-29 15:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("registration_number", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_students_registration_number", "students", ["registration_number"], unique=True)
    op.create_index("ix_students_email", "students", ["email"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("plate", sa.String(length=10), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_vehicles_student_id_students"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_vehicles_plate", "vehicles", ["plate"], unique=True)
    op.create_index("ix_vehicles_student_id", "vehicles", ["student_id"], unique=False)

    op.create_table(
        "plate_reads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=True),
        sa.Column("plate", sa.String(length=10), nullable=False),
        sa.Column("source", sa.String(length=30), server_default="manual", nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("image_path", sa.String(length=255), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], name=op.f("fk_plate_reads_vehicle_id_vehicles"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plate_reads")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_plate_reads_plate", "plate_reads", ["plate"], unique=False)
    op.create_index("ix_plate_reads_read_at", "plate_reads", ["read_at"], unique=False)

    op.create_table(
        "access_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("plate_read_id", sa.Integer(), nullable=True),
        sa.Column("plate", sa.String(length=10), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("event_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["plate_read_id"], ["plate_reads.id"], name=op.f("fk_access_events_plate_read_id_plate_reads"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_access_events_student_id_students"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], name=op.f("fk_access_events_vehicle_id_vehicles"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_events")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_access_events_event_at", "access_events", ["event_at"], unique=False)
    op.create_index("ix_access_events_plate", "access_events", ["plate"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_name", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=50), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_entity_name", "audit_logs", ["entity_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_name", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_access_events_plate", table_name="access_events")
    op.drop_index("ix_access_events_event_at", table_name="access_events")
    op.drop_table("access_events")

    op.drop_index("ix_plate_reads_read_at", table_name="plate_reads")
    op.drop_index("ix_plate_reads_plate", table_name="plate_reads")
    op.drop_table("plate_reads")

    op.drop_index("ix_vehicles_student_id", table_name="vehicles")
    op.drop_index("ix_vehicles_plate", table_name="vehicles")
    op.drop_table("vehicles")

    op.drop_index("ix_students_email", table_name="students")
    op.drop_index("ix_students_registration_number", table_name="students")
    op.drop_table("students")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

