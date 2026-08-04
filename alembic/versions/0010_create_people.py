"""Create people and copy existing students without changing legacy links.

Revision ID: 0010_create_people
Revises: 0009_vehicle_domains
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0010_create_people"
down_revision: str | None = "0009_vehicle_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PEOPLE = "tblpessoas"
STUDENTS = "tblalunos"
DOMAINS = "tbldominios"
ACTIVE_REGISTRATION = "strmatriculaativa"
INDEXES = (
    ("idx_tblpessoas_strtipopessoa", "strtipopessoa", False),
    ("idx_tblpessoas_strmatricula", "strmatricula", False),
    ("idx_tblpessoas_bolativo", "bolativo", False),
    ("idx_tblpessoas_numcursoid", "numcursoid", False),
    ("uq_tblpessoas_strmatriculaativa", ACTIVE_REGISTRATION, True),
)


def _inspector():
    return inspect(op.get_bind())


def _columns(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names() -> set[str]:
    if not _inspector().has_table(PEOPLE):
        return set()
    return {index["name"] for index in _inspector().get_indexes(PEOPLE)}


def _course_fk_exists() -> bool:
    if not _inspector().has_table(PEOPLE):
        return False
    for foreign_key in _inspector().get_foreign_keys(PEOPLE):
        if (
            foreign_key.get("name") == "fk_tblpessoas_curso"
            or (
                foreign_key.get("constrained_columns") == ["numcursoid"]
                and foreign_key.get("referred_table") == DOMAINS
                and foreign_key.get("referred_columns") == ["numdominioid"]
            )
        ):
            return True
    return False


def _has_duplicate_active_registrations() -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT strmatricula
                FROM {PEOPLE}
                WHERE bolativo = 1
                GROUP BY strmatricula
                HAVING COUNT(*) > 1
            ) duplicates
            """
        )
    )
    return int(result.scalar_one()) > 0


def _has_orphan_courses() -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {PEOPLE} person
            LEFT JOIN {DOMAINS} domain_row
              ON domain_row.numdominioid = person.numcursoid
            WHERE person.numcursoid IS NOT NULL
              AND domain_row.numdominioid IS NULL
            """
        )
    )
    return int(result.scalar_one()) > 0


def _copy_students() -> None:
    people_columns = _columns(PEOPLE)
    student_columns = _columns(STUDENTS)
    required_people = {
        "strtipopessoa", "strmatricula", "strnomecompleto", "stremail",
        "strtelefone", "bolativo", "dtacriacao", "dtaatualizacao",
    }
    required_students = {
        "strmatricula", "strnomecompleto", "stremail", "strtelefone",
        "bolativo", "dtacriacao", "dtaatualizacao",
    }
    if not required_people.issubset(people_columns):
        return
    if not required_students.issubset(student_columns):
        return
    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {PEOPLE} (
                strtipopessoa, strmatricula, strnomecompleto, stremail,
                strtelefone, numcursoid, bolativo, dtacriacao, dtaatualizacao
            )
            SELECT
                'ALUNO', student.strmatricula, student.strnomecompleto,
                student.stremail, student.strtelefone, NULL, student.bolativo,
                student.dtacriacao, student.dtaatualizacao
            FROM {STUDENTS} student
            WHERE NOT EXISTS (
                SELECT 1 FROM {PEOPLE} person
                WHERE person.strtipopessoa = 'ALUNO'
                  AND person.strmatricula = student.strmatricula
            )
              AND NOT EXISTS (
                SELECT 1 FROM {PEOPLE} active_person
                WHERE student.bolativo = 1
                  AND active_person.bolativo = 1
                  AND active_person.strmatricula = student.strmatricula
            )
            """
        )
    )


def upgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table(PEOPLE):
        op.create_table(
            PEOPLE,
            sa.Column("numpessoaid", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("strtipopessoa", sa.String(length=20), nullable=False),
            sa.Column("strmatricula", sa.String(length=50), nullable=False),
            sa.Column("strnomecompleto", sa.String(length=255), nullable=False),
            sa.Column("stremail", sa.String(length=255), nullable=True),
            sa.Column("strtelefone", sa.String(length=20), nullable=True),
            sa.Column("numcursoid", sa.Integer(), nullable=True),
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column(
                ACTIVE_REGISTRATION, sa.String(length=50),
                sa.Computed(
                    "CASE WHEN bolativo = 1 THEN strmatricula ELSE NULL END",
                    persisted=True,
                ), nullable=True,
            ),
            sa.Column(
                "dtacriacao", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "strtipopessoa IN ('ALUNO', 'FUNCIONARIO')",
                name="ck_tblpessoas_tipopessoa",
            ),
            sa.PrimaryKeyConstraint("numpessoaid", name="pk_tblpessoas"),
            mysql_engine="InnoDB", mysql_charset="utf8mb4",
        )

    columns = _columns(PEOPLE)
    if ACTIVE_REGISTRATION not in columns and {"bolativo", "strmatricula"}.issubset(columns):
        op.add_column(
            PEOPLE,
            sa.Column(
                ACTIVE_REGISTRATION, sa.String(length=50),
                sa.Computed(
                    "CASE WHEN bolativo = 1 THEN strmatricula ELSE NULL END",
                    persisted=True,
                ), nullable=True,
            ),
        )
        columns = _columns(PEOPLE)

    if _inspector().has_table(STUDENTS):
        _copy_students()

    index_names = _index_names()
    for index_name, column_name, unique in INDEXES:
        if column_name not in columns or index_name in index_names:
            continue
        if unique and _has_duplicate_active_registrations():
            continue
        op.create_index(index_name, PEOPLE, [column_name], unique=unique)
        index_names.add(index_name)

    if (
        "numcursoid" in columns
        and _inspector().has_table(DOMAINS)
        and "numdominioid" in _columns(DOMAINS)
        and not _course_fk_exists()
        and not _has_orphan_courses()
    ):
        op.create_foreign_key(
            "fk_tblpessoas_curso", PEOPLE, DOMAINS,
            ["numcursoid"], ["numdominioid"], ondelete="RESTRICT",
        )


def downgrade() -> None:
    # Non-destructive by project policy: people and copied student data are retained.
    pass
