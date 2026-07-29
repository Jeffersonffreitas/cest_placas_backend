"""Create the domain options table defensively.

Revision ID: 0008_create_domains
Revises: 0007_column_names_lowercase
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0008_create_domains"
down_revision: str | None = "0007_column_names_lowercase"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "tbldominios"


def _inspector():
    return inspect(op.get_bind())


def _index_names() -> set[str]:
    if not _inspector().has_table(TABLE_NAME):
        return set()
    return {index["name"] for index in _inspector().get_indexes(TABLE_NAME)}


def _column_names() -> set[str]:
    if not _inspector().has_table(TABLE_NAME):
        return set()
    return {column["name"] for column in _inspector().get_columns(TABLE_NAME)}


def upgrade() -> None:
    if not _inspector().has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("numdominioid", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("strtipo", sa.String(length=50), nullable=False),
            sa.Column("strcodigo", sa.String(length=100), nullable=True),
            sa.Column("strnome", sa.String(length=255), nullable=False),
            sa.Column("numdominiopaiid", sa.Integer(), nullable=True),
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["numdominiopaiid"], ["tbldominios.numdominioid"],
                name="fk_tbldominios_pai", ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("numdominioid", name="pk_tbldominios"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )

    columns = _column_names()
    indexes = _index_names()
    requested_indexes = (
        ("ix_tbldominios_tipo", "strtipo"),
        ("ix_tbldominios_ativo", "bolativo"),
        ("ix_tbldominios_pai", "numdominiopaiid"),
    )
    for index_name, column_name in requested_indexes:
        if column_name in columns and index_name not in indexes:
            op.create_index(index_name, TABLE_NAME, [column_name], unique=False)


def downgrade() -> None:
    # Intentionally non-destructive: project policy forbids dropping tables or data.
    pass
