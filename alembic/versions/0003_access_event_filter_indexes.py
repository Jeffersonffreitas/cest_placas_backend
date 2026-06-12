"""access event filter indexes

Revision ID: 0003_access_event_filter_indexes
Revises: 0002_access_events_manual_plate_reads
Create Date: 2026-05-14 14:45:00
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "0003_access_event_filter_indexes"
down_revision: Union[str, None] = "0002_access_events_manual_plate_reads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspect(op.get_bind()).get_indexes(table_name))


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name) and set(columns).issubset(_table_columns(table_name)):
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    _create_index_if_missing("access_events", "ix_access_events_status", ["status"])
    _create_index_if_missing("access_events", "ix_access_events_student_id", ["student_id"])
    _create_index_if_missing("access_events", "ix_access_events_vehicle_id", ["vehicle_id"])


def downgrade() -> None:
    _drop_index_if_exists("access_events", "ix_access_events_vehicle_id")
    _drop_index_if_exists("access_events", "ix_access_events_student_id")
    _drop_index_if_exists("access_events", "ix_access_events_status")
