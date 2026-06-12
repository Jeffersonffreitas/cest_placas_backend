"""access events for manual plate reads

Revision ID: 0002_access_events_manual_plate_reads
Revises: 0001_initial_schema
Create Date: 2026-05-12 15:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0002_access_events_manual_plate_reads"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspect(op.get_bind()).get_indexes(table_name))


def _foreign_key_exists(table_name: str, constraint_name: str) -> bool:
    expected_name = str(constraint_name)
    return any(
        foreign_key["name"] == expected_name
        for foreign_key in inspect(op.get_bind()).get_foreign_keys(table_name)
    )


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str], *, unique: bool = False) -> None:
    existing_columns = _table_columns(table_name)
    existing_indexes = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in existing_indexes and set(columns).issubset(existing_columns):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_foreign_key_if_exists(table_name: str, constraint_name: str) -> None:
    if _foreign_key_exists(table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _table_columns(table_name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if column_name in _table_columns(table_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _drop_index_if_exists("access_events", "ix_access_events_plate")
    _drop_index_if_exists("access_events", "ix_access_events_event_at")
    _drop_foreign_key_if_exists("access_events", op.f("fk_access_events_plate_read_id_plate_reads"))

    _add_column_if_missing("access_events", sa.Column("plate_input", sa.String(length=20), nullable=True))
    _add_column_if_missing("access_events", sa.Column("plate_normalized", sa.String(length=10), nullable=True))
    _add_column_if_missing(
        "access_events",
        sa.Column("source", sa.String(length=30), server_default="manual", nullable=False),
    )

    columns = _table_columns("access_events")
    if {"plate_input", "plate_normalized", "plate"}.issubset(columns):
        op.execute("UPDATE access_events SET plate_input = plate, plate_normalized = plate")
    if "status" in columns:
        op.execute("UPDATE access_events SET status = 'not_found' WHERE status NOT IN ('matched', 'not_found')")

    columns = _table_columns("access_events")
    if "plate_input" in columns:
        op.alter_column(
            "access_events",
            "plate_input",
            existing_type=sa.String(length=20),
            nullable=False,
        )
    if "plate_normalized" in columns:
        op.alter_column(
            "access_events",
            "plate_normalized",
            existing_type=sa.String(length=10),
            nullable=False,
        )
    if "status" in columns:
        op.alter_column(
            "access_events",
            "status",
            existing_type=sa.String(length=30),
            type_=sa.String(length=20),
            existing_nullable=False,
            existing_server_default="pending",
            server_default=None,
        )

    _drop_column_if_exists("access_events", "plate_read_id")
    _drop_column_if_exists("access_events", "plate")
    _drop_column_if_exists("access_events", "direction")
    _drop_column_if_exists("access_events", "notes")
    _drop_column_if_exists("access_events", "event_at")
    _drop_column_if_exists("access_events", "updated_at")

    _create_index_if_missing("access_events", "ix_access_events_plate_normalized", ["plate_normalized"])
    _create_index_if_missing("access_events", "ix_access_events_created_at", ["created_at"])


def downgrade() -> None:
    _drop_index_if_exists("access_events", "ix_access_events_created_at")
    _drop_index_if_exists("access_events", "ix_access_events_plate_normalized")

    _add_column_if_missing("access_events", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    _add_column_if_missing("access_events", sa.Column("event_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("access_events", sa.Column("notes", sa.Text(), nullable=True))
    _add_column_if_missing("access_events", sa.Column("direction", sa.String(length=20), nullable=True))
    _add_column_if_missing("access_events", sa.Column("plate", sa.String(length=10), nullable=True))
    _add_column_if_missing("access_events", sa.Column("plate_read_id", sa.Integer(), nullable=True))

    columns = _table_columns("access_events")
    if {"plate", "plate_normalized", "event_at", "created_at"}.issubset(columns):
        op.execute("UPDATE access_events SET plate = plate_normalized, event_at = created_at")

    columns = _table_columns("access_events")
    if "plate" in columns:
        op.alter_column("access_events", "plate", existing_type=sa.String(length=10), nullable=False)
    if "event_at" in columns:
        op.alter_column("access_events", "event_at", existing_type=sa.DateTime(), nullable=False)
    if "status" in columns:
        op.alter_column(
            "access_events",
            "status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
            server_default="pending",
        )

    _drop_column_if_exists("access_events", "source")
    _drop_column_if_exists("access_events", "plate_normalized")
    _drop_column_if_exists("access_events", "plate_input")

    if not _foreign_key_exists("access_events", op.f("fk_access_events_plate_read_id_plate_reads")):
        columns = _table_columns("access_events")
        plate_reads_columns = _table_columns("plate_reads")
        if "plate_read_id" in columns and "id" in plate_reads_columns:
            op.create_foreign_key(
                op.f("fk_access_events_plate_read_id_plate_reads"),
                "access_events",
                "plate_reads",
                ["plate_read_id"],
                ["id"],
                ondelete="SET NULL",
            )
    _create_index_if_missing("access_events", "ix_access_events_event_at", ["event_at"])
    _create_index_if_missing("access_events", "ix_access_events_plate", ["plate"])
