"""add access event source index

Revision ID: 0004_access_event_source_index
Revises: 0003_access_event_filter_indexes
Create Date: 2026-05-18 17:10:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0004_access_event_source_index"
down_revision: Union[str, None] = "0003_access_event_filter_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_access_events_source", "access_events", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_access_events_source", table_name="access_events")
