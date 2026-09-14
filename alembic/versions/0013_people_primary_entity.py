"""Allow visitors and scope active registration uniqueness by person type.

Revision ID: 0013_people_primary_entity
Revises: 0012_integer_column_prefixes
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0013_people_primary_entity"
down_revision: str | None = "0012_integer_column_prefixes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PEOPLE = "tblpessoas"
TYPE_CHECK = "ck_tblpessoas_tipopessoa"
OLD_UNIQUE = "uq_tblpessoas_strmatriculaativa"
NEW_UNIQUE = "uq_tblpessoas_tipo_matriculaativa"
TYPE_EXPRESSION = "strtipopessoa IN ('ALUNO', 'FUNCIONARIO', 'VISITANTE')"


def _inspector():
    return inspect(op.get_bind())


def _table_exists() -> bool:
    inspector = _inspector()
    return PEOPLE in inspector.get_table_names() or inspector.has_table(PEOPLE)


def _check_constraints() -> dict[str, dict]:
    return {
        constraint["name"]: constraint
        for constraint in _inspector().get_check_constraints(PEOPLE)
        if constraint.get("name")
    }


def _indexes() -> dict[str, dict]:
    return {
        index["name"]: index
        for index in _inspector().get_indexes(PEOPLE)
        if index.get("name")
    }


def _replace_type_check(expression: str) -> None:
    checks = _check_constraints()
    current = checks.get(TYPE_CHECK)
    current_sql = str(current.get("sqltext", "")).upper() if current else ""
    if expression.upper() in current_sql:
        return

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(PEOPLE) as batch_op:
            if current is not None:
                batch_op.drop_constraint(TYPE_CHECK, type_="check")
            batch_op.create_check_constraint(TYPE_CHECK, expression)
        return

    if current is not None:
        op.drop_constraint(TYPE_CHECK, PEOPLE, type_="check")
    op.create_check_constraint(TYPE_CHECK, PEOPLE, expression)


def _replace_active_registration_index() -> None:
    indexes = _indexes()
    old_index = indexes.get(OLD_UNIQUE)
    new_index = indexes.get(NEW_UNIQUE)
    expected_columns = ["strtipopessoa", "strmatriculaativa"]
    if old_index is not None:
        op.drop_index(OLD_UNIQUE, table_name=PEOPLE)
    if new_index is None or new_index.get("column_names") != expected_columns:
        if new_index is not None:
            op.drop_index(NEW_UNIQUE, table_name=PEOPLE)
        op.create_index(NEW_UNIQUE, PEOPLE, expected_columns, unique=True)


def upgrade() -> None:
    if not _table_exists():
        return
    columns = {column["name"] for column in _inspector().get_columns(PEOPLE)}
    if "strtipopessoa" in columns:
        _replace_type_check(TYPE_EXPRESSION)
    if {"strtipopessoa", "strmatriculaativa"}.issubset(columns):
        _replace_active_registration_index()


def downgrade() -> None:
    # Non-destructive: VISITANTE rows may already exist after this migration.
    pass
