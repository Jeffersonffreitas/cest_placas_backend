"""access event filter indexes

Revision ID: 0003_access_event_filter_indexes
Revises: 0002_access_events_manual_plate_reads
Create Date: 2026-05-14 14:45:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0003_access_event_filter_indexes"
down_revision: Union[str, None] = "0002_access_events_manual_plate_reads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_access_events_status", "access_events", ["status"], unique=False)
    op.create_index("ix_access_events_student_id", "access_events", ["student_id"], unique=False)
    op.create_index("ix_access_events_vehicle_id", "access_events", ["vehicle_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_access_events_vehicle_id", table_name="access_events")
    op.drop_index("ix_access_events_student_id", table_name="access_events")
    op.drop_index("ix_access_events_status", table_name="access_events")
