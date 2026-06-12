"""add access event source index

Revision ID: 0004_access_event_source_index
Revises: 0003_access_event_filter_indexes
Create Date: 2026-05-18 17:10:00
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "0004_access_event_source_index"
down_revision: Union[str, None] = "0003_access_event_filter_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspect(op.get_bind()).get_indexes(table_name))


def upgrade() -> None:
    if not _index_exists("access_events", "ix_access_events_source") and "source" in _table_columns("access_events"):
        op.create_index("ix_access_events_source", "access_events", ["source"], unique=False)


def downgrade() -> None:
    if _index_exists("access_events", "ix_access_events_source"):
        op.drop_index("ix_access_events_source", table_name="access_events")
