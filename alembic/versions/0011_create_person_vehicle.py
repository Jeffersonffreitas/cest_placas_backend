"""Create the person-vehicle association and copy legacy student links.

Revision ID: 0011_create_person_vehicle
Revises: 0010_create_people
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0011_create_person_vehicle"
down_revision: str | None = "0010_create_people"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINKS = "tblpessoaveiculo"
PEOPLE = "tblpessoas"
VEHICLES = "tblveiculos"
STUDENTS = "tblalunos"
INDEXES = (
    ("idx_tblpessoaveiculo_numpessoaid", "numpessoaid", False),
    ("idx_tblpessoaveiculo_numveiculoid", "numveiculoid", False),
    ("idx_tblpessoaveiculo_bolativo", "bolativo", False),
    ("uq_tblpessoaveiculo_pessoa_veiculo", ("numpessoaid", "numveiculoid"), True),
)


def _inspector():
    return inspect(op.get_bind())


def _columns(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_and_unique_names() -> set[str]:
    if not _inspector().has_table(LINKS):
        return set()
    inspector = _inspector()
    names = {index["name"] for index in inspector.get_indexes(LINKS)}
    names.update(
        constraint["name"] for constraint in inspector.get_unique_constraints(LINKS)
        if constraint.get("name")
    )
    return names


def _foreign_key_exists(
    name: str, column_name: str, target_table: str, target_column: str,
) -> bool:
    if not _inspector().has_table(LINKS):
        return False
    for foreign_key in _inspector().get_foreign_keys(LINKS):
        if foreign_key.get("name") == name:
            return True
        if (
            foreign_key.get("constrained_columns") == [column_name]
            and foreign_key.get("referred_table") == target_table
            and foreign_key.get("referred_columns") == [target_column]
        ):
            return True
    return False


def _has_orphans(column_name: str, target_table: str, target_column: str) -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {LINKS} link_row
            LEFT JOIN {target_table} target_row
              ON target_row.{target_column} = link_row.{column_name}
            WHERE link_row.{column_name} IS NOT NULL
              AND target_row.{target_column} IS NULL
            """
        )
    )
    return int(result.scalar_one()) > 0


def _has_duplicate_pairs() -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT numpessoaid, numveiculoid
                FROM {LINKS}
                GROUP BY numpessoaid, numveiculoid
                HAVING COUNT(*) > 1
            ) duplicate_pairs
            """
        )
    )
    return int(result.scalar_one()) > 0


def _copy_legacy_links() -> None:
    link_columns = _columns(LINKS)
    person_columns = _columns(PEOPLE)
    vehicle_columns = _columns(VEHICLES)
    student_columns = _columns(STUDENTS)
    if not {
        "numpessoaid", "numveiculoid", "bolativo", "dtacriacao", "dtaatualizacao",
    }.issubset(link_columns):
        return
    if not {
        "numpessoaid", "strtipopessoa", "strmatricula", "bolativo",
    }.issubset(person_columns):
        return
    if not {
        "numveiculoid", "numalunoid", "dtacriacao", "dtaatualizacao",
    }.issubset(vehicle_columns):
        return
    if not {"numalunoid", "strmatricula"}.issubset(student_columns):
        return

    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {LINKS} (
                numpessoaid, numveiculoid, bolativo, dtacriacao, dtaatualizacao
            )
            SELECT mapping.numpessoaid, vehicle.numveiculoid, 1,
                   vehicle.dtacriacao, vehicle.dtaatualizacao
            FROM {VEHICLES} vehicle
            JOIN {STUDENTS} student
              ON student.numalunoid = vehicle.numalunoid
            JOIN (
                SELECT person.strmatricula,
                       COALESCE(
                           MIN(CASE WHEN person.bolativo = 1 THEN person.numpessoaid END),
                           MIN(person.numpessoaid)
                       ) AS numpessoaid
                FROM {PEOPLE} person
                WHERE person.strtipopessoa = 'ALUNO'
                GROUP BY person.strmatricula
            ) mapping ON mapping.strmatricula = student.strmatricula
            WHERE NOT EXISTS (
                SELECT 1 FROM {LINKS} existing_link
                WHERE existing_link.numpessoaid = mapping.numpessoaid
                  AND existing_link.numveiculoid = vehicle.numveiculoid
            )
            """
        )
    )


def upgrade() -> None:
    if not _inspector().has_table(LINKS):
        op.create_table(
            LINKS,
            sa.Column(
                "numpessoaveiculoid", sa.Integer(), autoincrement=True, nullable=False
            ),
            sa.Column("numpessoaid", sa.Integer(), nullable=False),
            sa.Column("numveiculoid", sa.Integer(), nullable=False),
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column(
                "dtacriacao", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("numpessoaveiculoid", name="pk_tblpessoaveiculo"),
            sa.UniqueConstraint(
                "numpessoaid", "numveiculoid",
                name="uq_tblpessoaveiculo_pessoa_veiculo",
            ),
            mysql_engine="InnoDB", mysql_charset="utf8mb4",
        )

    columns = _columns(LINKS)
    if (
        _inspector().has_table(PEOPLE)
        and _inspector().has_table(VEHICLES)
        and _inspector().has_table(STUDENTS)
    ):
        _copy_legacy_links()

    names = _index_and_unique_names()
    for index_name, column_spec, unique in INDEXES:
        column_names = (column_spec,) if isinstance(column_spec, str) else column_spec
        if not set(column_names).issubset(columns) or index_name in names:
            continue
        if unique and _has_duplicate_pairs():
            continue
        op.create_index(index_name, LINKS, list(column_names), unique=unique)
        names.add(index_name)

    foreign_keys = (
        (
            "fk_tblpessoaveiculo_pessoa", "numpessoaid",
            PEOPLE, "numpessoaid",
        ),
        (
            "fk_tblpessoaveiculo_veiculo", "numveiculoid",
            VEHICLES, "numveiculoid",
        ),
    )
    for name, column_name, target_table, target_column in foreign_keys:
        if column_name not in columns or not _inspector().has_table(target_table):
            continue
        if target_column not in _columns(target_table):
            continue
        if _foreign_key_exists(name, column_name, target_table, target_column):
            continue
        if _has_orphans(column_name, target_table, target_column):
            continue
        op.create_foreign_key(
            name, LINKS, target_table, [column_name], [target_column],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    # Non-destructive by project policy: the association table and links are retained.
    pass
