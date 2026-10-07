"""Prepare institutional people, courses, and coordinations.

Revision ID: 0016_institutional_people_courses
Revises: 0015_access_events_person_domains
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0016_institutional_people_courses"
down_revision: str | None = "0015_access_events_person_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COORDINATIONS = "tblcoordenacoes"
COURSES = "tblcursos"
PEOPLE = "tblpessoas"
DOMAINS = "tbldominios"


def _inspector():
    return inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    inspector = _inspector()
    return table_name in inspector.get_table_names() or inspector.has_table(table_name)


def _columns(table_name: str) -> dict[str, dict]:
    if not _table_exists(table_name):
        return {}
    return {column["name"]: column for column in _inspector().get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {
        index["name"]
        for index in _inspector().get_indexes(table_name)
        if index.get("name")
    }


def _create_tables() -> None:
    if not _table_exists(COORDINATIONS):
        op.create_table(
            COORDINATIONS,
            sa.Column("intcoordenacaoid", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("strnome", sa.String(length=255), nullable=False),
            sa.Column("strsigla", sa.String(length=50), nullable=True),
            sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.PrimaryKeyConstraint("intcoordenacaoid", name="pk_tblcoordenacoes"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )

    if not _table_exists(COURSES):
        op.create_table(
            COURSES,
            sa.Column("intcursoid", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("intcoordenacaoid", sa.Integer(), nullable=False),
            sa.Column("strnome", sa.String(length=255), nullable=False),
            sa.Column("strcodigo", sa.String(length=100), nullable=True),
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
                ["intcoordenacaoid"],
                [f"{COORDINATIONS}.intcoordenacaoid"],
                name="fk_tblcursos_coordenacao",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("intcursoid", name="pk_tblcursos"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )


def _create_indexes() -> None:
    definitions = {
        COORDINATIONS: (
            ("idx_tblcoordenacoes_strnome", "strnome"),
            ("idx_tblcoordenacoes_strsigla", "strsigla"),
            ("idx_tblcoordenacoes_bolativo", "bolativo"),
        ),
        COURSES: (
            ("idx_tblcursos_intcoordenacaoid", "intcoordenacaoid"),
            ("idx_tblcursos_strnome", "strnome"),
            ("idx_tblcursos_strcodigo", "strcodigo"),
            ("idx_tblcursos_bolativo", "bolativo"),
        ),
    }
    for table_name, indexes in definitions.items():
        existing = _index_names(table_name)
        columns = _columns(table_name)
        for index_name, column_name in indexes:
            if index_name not in existing and column_name in columns:
                op.create_index(index_name, table_name, [column_name], unique=False)
                existing.add(index_name)


def _legacy_course_rows() -> list[dict[str, object]]:
    if not (_table_exists(PEOPLE) and _table_exists(DOMAINS)):
        return []
    if "intcursoid" not in _columns(PEOPLE):
        return []
    required_domain_columns = {
        "intdominioid", "strtipo", "strnome", "strcodigo", "bolativo"
    }
    if not required_domain_columns.issubset(_columns(DOMAINS)):
        return []
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT DISTINCT
                domain_row.intdominioid AS id,
                domain_row.strnome AS name,
                domain_row.strcodigo AS code,
                domain_row.bolativo AS active
            FROM {DOMAINS} domain_row
            WHERE UPPER(domain_row.strtipo) = 'CURSO'
               OR EXISTS (
                    SELECT 1
                    FROM {PEOPLE} person
                    WHERE person.intcursoid = domain_row.intdominioid
               )
            """
        )
    )
    return [dict(row) for row in result.mappings().all()]


def _legacy_coordination_id() -> int:
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(
            f"SELECT intcoordenacaoid FROM {COORDINATIONS} "
            "WHERE strsigla = :acronym ORDER BY intcoordenacaoid"
        ),
        {"acronym": "LEGADO"},
    ).scalar()
    if existing is not None:
        return int(existing)
    bind.execute(
        sa.text(
            f"""
            INSERT INTO {COORDINATIONS}
                (strnome, strsigla, bolativo, dtacriacao, dtaatualizacao)
            VALUES
                (:name, :acronym, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {"name": "Coordenação de cursos legados", "acronym": "LEGADO"},
    )
    created = bind.execute(
        sa.text(
            f"SELECT intcoordenacaoid FROM {COORDINATIONS} "
            "WHERE strsigla = :acronym ORDER BY intcoordenacaoid"
        ),
        {"acronym": "LEGADO"},
    ).scalar_one()
    return int(created)


def _copy_legacy_courses() -> None:
    rows = _legacy_course_rows()
    if not rows:
        return
    coordination_id = _legacy_coordination_id()
    bind = op.get_bind()
    for row in rows:
        exists = bind.execute(
            sa.text(f"SELECT 1 FROM {COURSES} WHERE intcursoid = :course_id"),
            {"course_id": row["id"]},
        ).scalar()
        if exists is not None:
            continue
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {COURSES} (
                    intcursoid, intcoordenacaoid, strnome, strcodigo,
                    bolativo, dtacriacao, dtaatualizacao
                ) VALUES (
                    :course_id, :coordination_id, :name, :code,
                    :active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "course_id": row["id"],
                "coordination_id": coordination_id,
                "name": row["name"],
                "code": row["code"],
                "active": row["active"],
            },
        )


def _people_course_foreign_keys() -> list[dict]:
    if not _table_exists(PEOPLE):
        return []
    return [
        foreign_key
        for foreign_key in _inspector().get_foreign_keys(PEOPLE)
        if foreign_key.get("constrained_columns") == ["intcursoid"]
    ]


def _has_orphan_courses() -> bool:
    if not (_table_exists(PEOPLE) and _table_exists(COURSES)):
        return True
    count = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {PEOPLE} person
            LEFT JOIN {COURSES} course_row
              ON course_row.intcursoid = person.intcursoid
            WHERE person.intcursoid IS NOT NULL
              AND course_row.intcursoid IS NULL
            """
        )
    ).scalar_one()
    return int(count) > 0


def _rebuild_people_for_sqlite() -> None:
    """Rebuild without copying the generated column as a regular value."""
    columns = _columns(PEOPLE)
    supported_columns = {
        "intpessoaid",
        "strtipopessoa",
        "strmatricula",
        "strnomecompleto",
        "stremail",
        "strtelefone",
        "intcursoid",
        "bolativo",
        "strmatriculaativa",
        "dtacriacao",
        "dtaatualizacao",
    }
    required_columns = supported_columns - {"strmatriculaativa"}
    if not required_columns.issubset(columns):
        return
    # Do not risk losing columns introduced outside the known migration chain.
    if set(columns) - supported_columns:
        return

    existing_indexes = list(_inspector().get_indexes(PEOPLE))
    temporary_table = "_tmp_0016_tblpessoas"
    if _table_exists(temporary_table):
        op.drop_table(temporary_table)
    table_columns: list[sa.SchemaItem] = [
        sa.Column("intpessoaid", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strtipopessoa", sa.String(length=20), nullable=False),
        sa.Column("strmatricula", sa.String(length=50), nullable=True),
        sa.Column("strnomecompleto", sa.String(length=255), nullable=False),
        sa.Column("stremail", sa.String(length=255), nullable=True),
        sa.Column("strtelefone", sa.String(length=20), nullable=True),
        sa.Column("intcursoid", sa.Integer(), nullable=True),
        sa.Column("bolativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    ]
    if "strmatriculaativa" in columns:
        table_columns.append(
            sa.Column(
                "strmatriculaativa",
                sa.String(length=50),
                sa.Computed(
                    "CASE WHEN bolativo = 1 THEN strmatricula ELSE NULL END",
                    persisted=True,
                ),
                nullable=True,
            )
        )
    table_columns.extend(
        [
            sa.Column(
                "dtacriacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.Column(
                "dtaatualizacao", sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["intcursoid"],
                [f"{COURSES}.intcursoid"],
                name="fk_tblpessoas_curso",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("intpessoaid", name="pk_tblpessoas"),
        ]
    )
    op.create_table(temporary_table, *table_columns)

    copied_columns = [
        "intpessoaid",
        "strtipopessoa",
        "strmatricula",
        "strnomecompleto",
        "stremail",
        "strtelefone",
        "intcursoid",
        "bolativo",
        "dtacriacao",
        "dtaatualizacao",
    ]
    column_list = ", ".join(copied_columns)
    op.get_bind().execute(
        sa.text(
            f"INSERT INTO {temporary_table} ({column_list}) "
            f"SELECT {column_list} FROM {PEOPLE}"
        )
    )
    op.drop_table(PEOPLE)
    op.rename_table(temporary_table, PEOPLE)

    for index in existing_indexes:
        name = index.get("name")
        index_columns = index.get("column_names")
        if (
            name
            and index_columns
            and all(column_name in supported_columns for column_name in index_columns)
        ):
            op.create_index(
                name,
                PEOPLE,
                index_columns,
                unique=bool(index.get("unique", False)),
            )


def _adjust_people() -> None:
    columns = _columns(PEOPLE)
    if not columns:
        return
    registration = columns.get("strmatricula")
    foreign_keys = _people_course_foreign_keys()
    old_foreign_keys = [
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key.get("referred_table") != COURSES
    ]
    has_course_foreign_key = any(
        foreign_key.get("referred_table") == COURSES
        and foreign_key.get("referred_columns") == ["intcursoid"]
        for foreign_key in foreign_keys
    )
    can_switch_course = "intcursoid" in columns and not _has_orphan_courses()
    named_old_foreign_keys = [
        foreign_key for foreign_key in old_foreign_keys if foreign_key.get("name")
    ]
    can_drop_old_foreign_keys = len(named_old_foreign_keys) == len(old_foreign_keys)
    should_change_registration = bool(
        registration is not None and not registration.get("nullable", True)
    )
    should_switch_course = bool(
        can_switch_course
        and can_drop_old_foreign_keys
        and (old_foreign_keys or not has_course_foreign_key)
    )
    if not should_change_registration and not should_switch_course:
        return

    if op.get_bind().dialect.name == "sqlite":
        _rebuild_people_for_sqlite()
        return

    with op.batch_alter_table(PEOPLE) as batch_op:
        if should_change_registration:
            batch_op.alter_column(
                "strmatricula", existing_type=sa.String(length=50), nullable=True
            )
        if should_switch_course:
            for foreign_key in named_old_foreign_keys:
                batch_op.drop_constraint(foreign_key["name"], type_="foreignkey")
            if not has_course_foreign_key:
                batch_op.create_foreign_key(
                    "fk_tblpessoas_curso",
                    COURSES,
                    ["intcursoid"],
                    ["intcursoid"],
                    ondelete="RESTRICT",
                )


def upgrade() -> None:
    _create_tables()
    _create_indexes()
    _copy_legacy_courses()
    _adjust_people()


def downgrade() -> None:
    # Non-destructive by project policy: institutional structures are retained.
    pass
