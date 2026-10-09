"""Add logical access points, cameras, and plate-read location metadata.

Revision ID: 0017_access_points_cameras
Revises: 0016_institutional_people_courses
"""

from collections.abc import Sequence
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0017_access_points_cameras"
down_revision: str | None = "0016_institutional_people_courses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCESS_POINTS = "tblpontosacesso"
CAMERAS = "tblcameras"
PLATE_READS = "tblleiturasplacas"
ACCESS_EVENTS = "tbleventosacesso"


def _inspector():
    return inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    inspector = _inspector()
    return table_name in inspector.get_table_names() or inspector.has_table(table_name)


def _columns(table_name: str) -> dict[str, dict]:
    if not _table_exists(table_name):
        return {}
    return {column["name"]: column for column in _inspector().get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _table_exists(table_name) and column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_tables() -> None:
    if not _table_exists(ACCESS_POINTS):
        op.create_table(
            ACCESS_POINTS,
            sa.Column("intpontoacessoid", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("strnome", sa.String(length=255), nullable=False),
            sa.Column("strcodigo", sa.String(length=100), nullable=True),
            sa.Column("strsentido", sa.String(length=10), nullable=False),
            sa.Column("strdescricao", sa.String(length=500), nullable=True),
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.PrimaryKeyConstraint("intpontoacessoid", name="pk_tblpontosacesso"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
    else:
        _add_column_if_missing(
            ACCESS_POINTS, sa.Column("strnome", sa.String(length=255), nullable=True)
        )
        _add_column_if_missing(
            ACCESS_POINTS, sa.Column("strcodigo", sa.String(length=100), nullable=True)
        )
        _add_column_if_missing(
            ACCESS_POINTS, sa.Column("strsentido", sa.String(length=10), nullable=True)
        )
        _add_column_if_missing(
            ACCESS_POINTS, sa.Column("strdescricao", sa.String(length=500), nullable=True)
        )
        _add_column_if_missing(
            ACCESS_POINTS,
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        )
        _add_column_if_missing(
            ACCESS_POINTS,
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
        )
        _add_column_if_missing(
            ACCESS_POINTS,
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
        )

    if not _table_exists(CAMERAS):
        op.create_table(
            CAMERAS,
            sa.Column("intcameraid", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("intpontoacessoid", sa.Integer(), nullable=False),
            sa.Column("strnome", sa.String(length=255), nullable=False),
            sa.Column("strcodigo", sa.String(length=100), nullable=False),
            sa.Column("strdescricao", sa.String(length=500), nullable=True),
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["intpontoacessoid"],
                [f"{ACCESS_POINTS}.intpontoacessoid"],
                name="fk_tblcameras_pontoacesso",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("intcameraid", name="pk_tblcameras"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
    else:
        _add_column_if_missing(
            CAMERAS, sa.Column("intpontoacessoid", sa.Integer(), nullable=True)
        )
        _add_column_if_missing(
            CAMERAS, sa.Column("strnome", sa.String(length=255), nullable=True)
        )
        _add_column_if_missing(
            CAMERAS, sa.Column("strcodigo", sa.String(length=100), nullable=True)
        )
        _add_column_if_missing(
            CAMERAS, sa.Column("strdescricao", sa.String(length=500), nullable=True)
        )
        _add_column_if_missing(
            CAMERAS,
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        )
        _add_column_if_missing(
            CAMERAS,
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
        )
        _add_column_if_missing(
            CAMERAS,
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
        )


def _add_read_and_event_columns() -> None:
    _add_column_if_missing(
        PLATE_READS, sa.Column("intcameraid", sa.Integer(), nullable=True)
    )
    _add_column_if_missing(
        PLATE_READS,
        sa.Column(
            "strladoveiculo", sa.String(length=10),
            server_default="INDEFINIDO", nullable=False,
        ),
    )
    _add_column_if_missing(
        ACCESS_EVENTS, sa.Column("intpontoacessoid", sa.Integer(), nullable=True)
    )


def _index_exists(
    table_name: str, name: str, columns: tuple[str, ...], *, unique: bool
) -> bool:
    if not _table_exists(table_name):
        return False
    for index in _inspector().get_indexes(table_name):
        if index.get("name") == name:
            return True
        if (
            tuple(index.get("column_names") or ()) == columns
            and bool(index.get("unique", False)) == unique
        ):
            return True
    return False


def _has_duplicate_values(table_name: str, column_name: str) -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"SELECT 1 FROM {table_name} WHERE {column_name} IS NOT NULL "
            f"GROUP BY {column_name} HAVING COUNT(*) > 1"
        )
    ).first()
    return result is not None


def _create_indexes() -> None:
    definitions = (
        (ACCESS_POINTS, "idx_tblpontosacesso_strnome", ("strnome",), False),
        (ACCESS_POINTS, "idx_tblpontosacesso_strsentido", ("strsentido",), False),
        (ACCESS_POINTS, "idx_tblpontosacesso_bolativo", ("bolativo",), False),
        (CAMERAS, "idx_tblcameras_intpontoacessoid", ("intpontoacessoid",), False),
        (CAMERAS, "uq_tblcameras_strcodigo", ("strcodigo",), True),
        (CAMERAS, "idx_tblcameras_strnome", ("strnome",), False),
        (CAMERAS, "idx_tblcameras_bolativo", ("bolativo",), False),
        (PLATE_READS, "idx_tblleiturasplacas_intcameraid", ("intcameraid",), False),
        (
            ACCESS_EVENTS, "idx_tbleventosacesso_intpontoacessoid",
            ("intpontoacessoid",), False,
        ),
    )
    for table_name, name, columns, unique in definitions:
        if not set(columns).issubset(_columns(table_name)):
            continue
        if _index_exists(table_name, name, columns, unique=unique):
            continue
        if unique and _has_duplicate_values(table_name, columns[0]):
            continue
        op.create_index(name, table_name, list(columns), unique=unique)


def _foreign_key_exists(
    table_name: str, name: str, columns: tuple[str, ...], target: str,
    target_columns: tuple[str, ...],
) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        foreign_key.get("name") == name
        or (
            tuple(foreign_key.get("constrained_columns") or ()) == columns
            and foreign_key.get("referred_table") == target
            and tuple(foreign_key.get("referred_columns") or ()) == target_columns
        )
        for foreign_key in _inspector().get_foreign_keys(table_name)
    )


def _has_orphans(
    table_name: str, column_name: str, target: str, target_column: str
) -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"SELECT 1 FROM {table_name} source_row "
            f"LEFT JOIN {target} target_row "
            f"ON target_row.{target_column} = source_row.{column_name} "
            f"WHERE source_row.{column_name} IS NOT NULL "
            f"AND target_row.{target_column} IS NULL"
        )
    ).first()
    return result is not None


def _create_foreign_key(
    table_name: str, name: str, column_name: str, target: str,
    target_column: str, ondelete: str,
) -> None:
    if not (_table_exists(table_name) and _table_exists(target)):
        return
    if column_name not in _columns(table_name) or target_column not in _columns(target):
        return
    if _foreign_key_exists(
        table_name, name, (column_name,), target, (target_column,)
    ):
        return
    if _has_orphans(table_name, column_name, target, target_column):
        return
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_foreign_key(
                name, target, [column_name], [target_column], ondelete=ondelete
            )
    else:
        op.create_foreign_key(
            name, table_name, target, [column_name], [target_column],
            ondelete=ondelete,
        )


def _create_foreign_keys() -> None:
    _create_foreign_key(
        CAMERAS, "fk_tblcameras_pontoacesso", "intpontoacessoid",
        ACCESS_POINTS, "intpontoacessoid", "RESTRICT",
    )
    _create_foreign_key(
        PLATE_READS, "fk_tblleiturasplacas_camera", "intcameraid",
        CAMERAS, "intcameraid", "SET NULL",
    )
    _create_foreign_key(
        ACCESS_EVENTS, "fk_tbleventosacesso_pontoacesso", "intpontoacessoid",
        ACCESS_POINTS, "intpontoacessoid", "SET NULL",
    )


def _normalize_check_clause(clause: object) -> str:
    normalized = str(clause or "").lower()
    normalized = re.sub(r"_(?:utf8mb4|utf8|latin1)", "", normalized)
    normalized = re.sub(r"[\s`\"()]", "", normalized)
    return normalized


def _mysql_check_constraints(table_name: str) -> list[dict[str, object]]:
    result = op.get_bind().execute(
        sa.text(
            """
            SELECT
                tc.CONSTRAINT_NAME AS name,
                cc.CHECK_CLAUSE AS sqltext
            FROM information_schema.TABLE_CONSTRAINTS AS tc
            JOIN information_schema.CHECK_CONSTRAINTS AS cc
              ON cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
             AND cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            WHERE tc.CONSTRAINT_SCHEMA = DATABASE()
              AND tc.TABLE_NAME = :table_name
              AND tc.CONSTRAINT_TYPE = 'CHECK'
            """
        ),
        {"table_name": table_name},
    )
    return [dict(row) for row in result.mappings().all()]


def _check_constraints(table_name: str) -> list[dict[str, object]]:
    if not _table_exists(table_name):
        return []
    if op.get_bind().dialect.name in {"mysql", "mariadb"}:
        return _mysql_check_constraints(table_name)
    return list(_inspector().get_check_constraints(table_name))


def _check_exists(table_name: str, name: str, condition: str) -> bool:
    expected_clause = _normalize_check_clause(condition)
    known_names = {
        name.lower(),
        f"ck_{table_name}_{name}".lower(),
    }
    for constraint in _check_constraints(table_name):
        existing_name = str(constraint.get("name") or "").lower()
        existing_clause = _normalize_check_clause(
            constraint.get("sqltext") or constraint.get("check_clause")
        )
        if existing_name in known_names or existing_clause == expected_clause:
            return True
    return False


def _create_check(table_name: str, name: str, condition: str) -> None:
    if not _table_exists(table_name) or _check_exists(table_name, name, condition):
        return
    finalized_name = op.f(name)
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_check_constraint(finalized_name, condition)
    else:
        op.create_check_constraint(finalized_name, table_name, condition)


def _create_checks() -> None:
    _create_check(
        ACCESS_POINTS,
        "ck_tblpontosacesso_sentido",
        "strsentido IN ('ENTRADA', 'SAIDA', 'MISTO')",
    )
    _create_check(
        PLATE_READS,
        "ck_tblleiturasplacas_ladoveiculo",
        "strladoveiculo IN ('FRONTAL', 'TRASEIRA', 'INDEFINIDO')",
    )


def upgrade() -> None:
    _create_tables()
    _add_read_and_event_columns()
    _create_indexes()
    _create_foreign_keys()
    _create_checks()


def downgrade() -> None:
    # Non-destructive by project policy: new structures and historical links remain.
    pass
