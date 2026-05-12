"""access events for manual plate reads

Revision ID: 0002_access_events_manual_plate_reads
Revises: 0001_initial_schema
Create Date: 2026-05-12 15:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_access_events_manual_plate_reads"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_access_events_plate", table_name="access_events")
    op.drop_index("ix_access_events_event_at", table_name="access_events")
    op.drop_constraint(
        op.f("fk_access_events_plate_read_id_plate_reads"),
        "access_events",
        type_="foreignkey",
    )

    op.add_column("access_events", sa.Column("plate_input", sa.String(length=20), nullable=True))
    op.add_column("access_events", sa.Column("plate_normalized", sa.String(length=10), nullable=True))
    op.add_column(
        "access_events",
        sa.Column("source", sa.String(length=30), server_default="manual", nullable=False),
    )

    op.execute("UPDATE access_events SET plate_input = plate, plate_normalized = plate")
    op.execute("UPDATE access_events SET status = 'not_found' WHERE status NOT IN ('matched', 'not_found')")

    op.alter_column(
        "access_events",
        "plate_input",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.alter_column(
        "access_events",
        "plate_normalized",
        existing_type=sa.String(length=10),
        nullable=False,
    )
    op.alter_column(
        "access_events",
        "status",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default="pending",
        server_default=None,
    )

    op.drop_column("access_events", "plate_read_id")
    op.drop_column("access_events", "plate")
    op.drop_column("access_events", "direction")
    op.drop_column("access_events", "notes")
    op.drop_column("access_events", "event_at")
    op.drop_column("access_events", "updated_at")

    op.create_index("ix_access_events_plate_normalized", "access_events", ["plate_normalized"], unique=False)
    op.create_index("ix_access_events_created_at", "access_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_access_events_created_at", table_name="access_events")
    op.drop_index("ix_access_events_plate_normalized", table_name="access_events")

    op.add_column("access_events", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.add_column("access_events", sa.Column("event_at", sa.DateTime(), nullable=True))
    op.add_column("access_events", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("access_events", sa.Column("direction", sa.String(length=20), nullable=True))
    op.add_column("access_events", sa.Column("plate", sa.String(length=10), nullable=True))
    op.add_column("access_events", sa.Column("plate_read_id", sa.Integer(), nullable=True))

    op.execute("UPDATE access_events SET plate = plate_normalized, event_at = created_at")

    op.alter_column("access_events", "plate", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("access_events", "event_at", existing_type=sa.DateTime(), nullable=False)
    op.alter_column(
        "access_events",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
        server_default="pending",
    )

    op.drop_column("access_events", "source")
    op.drop_column("access_events", "plate_normalized")
    op.drop_column("access_events", "plate_input")

    op.create_foreign_key(
        op.f("fk_access_events_plate_read_id_plate_reads"),
        "access_events",
        "plate_reads",
        ["plate_read_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_access_events_event_at", "access_events", ["event_at"], unique=False)
    op.create_index("ix_access_events_plate", "access_events", ["plate"], unique=False)
