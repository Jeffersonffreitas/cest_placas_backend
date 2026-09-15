"""Remove the direct student dependency from vehicles.

Revision ID: 0014_remove_vehicle_student_dependency
Revises: 0013_people_primary_entity
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0014_remove_vehicle_student_dependency"
down_revision: str | None = "0013_people_primary_entity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VEHICLES = "tblveiculos"
STUDENTS = "tblalunos"
PEOPLE = "tblpessoas"
LINKS = "tblpessoaveiculo"
LEGACY_COLUMN = "intalunoid"


def _inspector():
    return inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    inspector = _inspector()
    return table_name in inspector.get_table_names() or inspector.has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _copy_legacy_links() -> None:
    required_tables = (VEHICLES, STUDENTS, PEOPLE, LINKS)
    if not all(_table_exists(table_name) for table_name in required_tables):
        return
    required_columns = {
        VEHICLES: {"intveiculoid", LEGACY_COLUMN},
        STUDENTS: {"intalunoid", "strmatricula"},
        PEOPLE: {"intpessoaid", "strtipopessoa", "strmatricula", "bolativo"},
        LINKS: {
            "intpessoaid", "intveiculoid", "bolativo", "dtacriacao", "dtaatualizacao",
        },
    }
    if any(
        not columns.issubset(_columns(table_name))
        for table_name, columns in required_columns.items()
    ):
        return

    vehicle_columns = _columns(VEHICLES)
    created_at = (
        "vehicle.dtacriacao" if "dtacriacao" in vehicle_columns else "CURRENT_TIMESTAMP"
    )
    updated_at = (
        "vehicle.dtaatualizacao" if "dtaatualizacao" in vehicle_columns
        else "CURRENT_TIMESTAMP"
    )
    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {LINKS} (
                intpessoaid, intveiculoid, bolativo, dtacriacao, dtaatualizacao
            )
            SELECT mapping.intpessoaid, vehicle.intveiculoid, 1,
                   {created_at}, {updated_at}
            FROM {VEHICLES} vehicle
            JOIN {STUDENTS} student
              ON student.intalunoid = vehicle.{LEGACY_COLUMN}
            JOIN (
                SELECT person.strmatricula,
                       COALESCE(
                           MIN(CASE WHEN person.bolativo = 1 THEN person.intpessoaid END),
                           MIN(person.intpessoaid)
                       ) AS intpessoaid
                FROM {PEOPLE} person
                WHERE person.strtipopessoa = 'ALUNO'
                GROUP BY person.strmatricula
            ) mapping ON mapping.strmatricula = student.strmatricula
            WHERE vehicle.{LEGACY_COLUMN} IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM {LINKS} existing_link
                  WHERE existing_link.intpessoaid = mapping.intpessoaid
                    AND existing_link.intveiculoid = vehicle.intveiculoid
              )
            """
        )
    )


def _all_legacy_links_migrated() -> bool:
    if LEGACY_COLUMN not in _columns(VEHICLES):
        return True
    required_tables = (STUDENTS, PEOPLE, LINKS)
    if not all(_table_exists(table_name) for table_name in required_tables):
        return False
    required_columns = {
        STUDENTS: {"intalunoid", "strmatricula"},
        PEOPLE: {"intpessoaid", "strtipopessoa", "strmatricula"},
        LINKS: {"intpessoaid", "intveiculoid"},
    }
    if any(
        not columns.issubset(_columns(table_name))
        for table_name, columns in required_columns.items()
    ):
        return False
    missing = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {VEHICLES} vehicle
            WHERE vehicle.{LEGACY_COLUMN} IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM {STUDENTS} student
                  JOIN {PEOPLE} person
                    ON person.strtipopessoa = 'ALUNO'
                   AND person.strmatricula = student.strmatricula
                  JOIN {LINKS} link_row
                    ON link_row.intpessoaid = person.intpessoaid
                   AND link_row.intveiculoid = vehicle.intveiculoid
                  WHERE student.intalunoid = vehicle.{LEGACY_COLUMN}
              )
            """
        )
    ).scalar_one()
    return int(missing) == 0


def _legacy_foreign_keys() -> list[str]:
    if not _table_exists(VEHICLES):
        return []
    return [
        foreign_key["name"]
        for foreign_key in _inspector().get_foreign_keys(VEHICLES)
        if LEGACY_COLUMN in (foreign_key.get("constrained_columns") or [])
        and foreign_key.get("name")
    ]


def _legacy_indexes() -> list[str]:
    if not _table_exists(VEHICLES):
        return []
    return [
        index["name"]
        for index in _inspector().get_indexes(VEHICLES)
        if LEGACY_COLUMN in (index.get("column_names") or []) and index.get("name")
    ]


def _drop_legacy_column() -> None:
    if LEGACY_COLUMN not in _columns(VEHICLES):
        return
    foreign_keys = _legacy_foreign_keys()
    indexes = _legacy_indexes()
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(VEHICLES, recreate="always") as batch_op:
            for foreign_key in foreign_keys:
                batch_op.drop_constraint(foreign_key, type_="foreignkey")
            for index_name in indexes:
                batch_op.drop_index(index_name)
            batch_op.drop_column(LEGACY_COLUMN)
        return

    for foreign_key in foreign_keys:
        op.drop_constraint(foreign_key, VEHICLES, type_="foreignkey")
    for index_name in indexes:
        op.drop_index(index_name, table_name=VEHICLES)
    if LEGACY_COLUMN in _columns(VEHICLES):
        op.drop_column(VEHICLES, LEGACY_COLUMN)


def _make_legacy_column_nullable() -> None:
    legacy = next(
        (
            column
            for column in _inspector().get_columns(VEHICLES)
            if column["name"] == LEGACY_COLUMN
        ),
        None,
    )
    if legacy is None or legacy.get("nullable") is True:
        return
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(VEHICLES) as batch_op:
            batch_op.alter_column(
                LEGACY_COLUMN, existing_type=sa.Integer(), nullable=True
            )
        return
    op.alter_column(
        VEHICLES, LEGACY_COLUMN, existing_type=sa.Integer(), nullable=True
    )


def upgrade() -> None:
    if not _table_exists(VEHICLES) or LEGACY_COLUMN not in _columns(VEHICLES):
        return
    _copy_legacy_links()
    if _all_legacy_links_migrated():
        _drop_legacy_column()
    else:
        # Preserve unresolved data without making new vehicles depend on it.
        _make_legacy_column_nullable()


def downgrade() -> None:
    # Non-destructive: the N:N links remain the source of truth.
    pass
