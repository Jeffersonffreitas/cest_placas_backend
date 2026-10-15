import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Person, Student, Vehicle


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "0018_remove_legacy_students.py"
)


def _migration(connection):
    spec = importlib.util.spec_from_file_location(
        "migration_0018_remove_legacy_students", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    migration.op = Operations(MigrationContext.configure(connection))
    return migration


def _legacy_schema(
    connection,
    *,
    include_students: bool = True,
    include_event_student_id: bool = True,
    legacy_foreign_key_name: str | None = "fk_tbleventosacesso_aluno",
) -> dict[str, sa.Table]:
    metadata = sa.MetaData()
    people = sa.Table(
        "tblpessoas",
        metadata,
        sa.Column("intpessoaid", sa.Integer, primary_key=True),
        sa.Column("strtipopessoa", sa.String(20), nullable=False),
        sa.Column("strmatricula", sa.String(50)),
        sa.Column("strnomecompleto", sa.String(255), nullable=False),
        sa.Column("stremail", sa.String(255)),
        sa.Column("strtelefone", sa.String(20)),
        sa.Column("bolativo", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "dtacriacao", sa.DateTime, nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "dtaatualizacao", sa.DateTime, nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    students = None
    if include_students:
        students = sa.Table(
            "tblalunos",
            metadata,
            sa.Column("intalunoid", sa.Integer, primary_key=True),
            sa.Column("strmatricula", sa.String(50), nullable=False),
            sa.Column("strnomecompleto", sa.String(255), nullable=False),
            sa.Column("stremail", sa.String(255)),
            sa.Column("strtelefone", sa.String(20)),
            sa.Column("bolativo", sa.Boolean, nullable=False),
            sa.Column("dtacriacao", sa.DateTime, nullable=False),
            sa.Column("dtaatualizacao", sa.DateTime, nullable=False),
        )

    event_columns: list[sa.SchemaItem] = [
        sa.Column("inteventoacessoid", sa.Integer, primary_key=True),
        sa.Column("intpessoaid", sa.Integer),
    ]
    if include_event_student_id:
        event_columns.append(sa.Column("intalunoid", sa.Integer))
        if include_students:
            event_columns.append(
                sa.ForeignKeyConstraint(
                    ["intalunoid"],
                    ["tblalunos.intalunoid"],
                    name=legacy_foreign_key_name,
                    ondelete="SET NULL",
                )
            )
    events = sa.Table("tbleventosacesso", metadata, *event_columns)
    metadata.create_all(connection)
    return {"people": people, "students": students, "events": events}


def _legacy_student(student_id: int, registration: str, name: str) -> dict[str, object]:
    timestamp = datetime(2026, 1, 2, 3, 4, 5)
    return {
        "intalunoid": student_id,
        "strmatricula": registration,
        "strnomecompleto": name,
        "stremail": f"{registration.lower()}@example.com",
        "strtelefone": "85999999999",
        "bolativo": True,
        "dtacriacao": timestamp,
        "dtaatualizacao": timestamp,
    }


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "change_me"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_migration_preserves_students_and_events_and_is_idempotent() -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        tables = _legacy_schema(connection)
        people = tables["people"]
        students = tables["students"]
        events = tables["events"]
        assert students is not None
        connection.execute(
            people.insert(),
            {
                "intpessoaid": 10,
                "strtipopessoa": "ALUNO",
                "strmatricula": "A100",
                "strnomecompleto": "Aluno Existente",
                "bolativo": True,
            },
        )
        connection.execute(
            students.insert(),
            [
                _legacy_student(1, "A100", "Aluno Existente"),
                _legacy_student(2, "A200", "Aluno Migrado"),
            ],
        )
        connection.execute(
            events.insert(),
            [
                {"inteventoacessoid": 100, "intalunoid": 1, "intpessoaid": 10},
                {"inteventoacessoid": 200, "intalunoid": 2, "intpessoaid": None},
            ],
        )

        migration = _migration(connection)
        migration.upgrade()
        migration.upgrade()

        inspector = sa.inspect(connection)
        assert "tblalunos" not in inspector.get_table_names()
        assert "intalunoid" not in {
            column["name"] for column in inspector.get_columns("tbleventosacesso")
        }
        assert all(
            foreign_key.get("referred_table") != "tblalunos"
            for foreign_key in inspector.get_foreign_keys("tbleventosacesso")
        )

        migrated_people = sa.Table(
            "tblpessoas", sa.MetaData(), autoload_with=connection
        )
        people_rows = connection.execute(
            sa.select(migrated_people)
            .where(migrated_people.c.strtipopessoa == "ALUNO")
            .order_by(migrated_people.c.strmatricula)
        ).mappings().all()
        assert [row["strmatricula"] for row in people_rows] == ["A100", "A200"]
        assert people_rows[1]["strnomecompleto"] == "Aluno Migrado"
        assert people_rows[1]["stremail"] == "a200@example.com"
        assert people_rows[1]["strtelefone"] == "85999999999"
        assert people_rows[1]["bolativo"] is True

        migrated_events = sa.Table(
            "tbleventosacesso", sa.MetaData(), autoload_with=connection
        )
        event_rows = connection.execute(
            sa.select(migrated_events).order_by(migrated_events.c.inteventoacessoid)
        ).mappings().all()
        migrated_person_id = next(
            row["intpessoaid"]
            for row in people_rows
            if row["strmatricula"] == "A200"
        )
        assert [row["intpessoaid"] for row in event_rows] == [10, migrated_person_id]
    engine.dispose()


def test_migration_aborts_when_event_points_to_a_different_person() -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        tables = _legacy_schema(connection)
        people = tables["people"]
        students = tables["students"]
        events = tables["events"]
        assert students is not None
        connection.execute(
            people.insert(),
            [
                {
                    "intpessoaid": 10, "strtipopessoa": "ALUNO",
                    "strmatricula": "A100", "strnomecompleto": "Aluno",
                    "bolativo": True,
                },
                {
                    "intpessoaid": 20, "strtipopessoa": "FUNCIONARIO",
                    "strmatricula": "F100", "strnomecompleto": "Funcionario",
                    "bolativo": True,
                },
            ],
        )
        connection.execute(students.insert(), _legacy_student(1, "A100", "Aluno"))
        connection.execute(
            events.insert(),
            {"inteventoacessoid": 99, "intalunoid": 1, "intpessoaid": 20},
        )

        with pytest.raises(RuntimeError, match="event 99 points to person 20"):
            _migration(connection).upgrade()

        inspector = sa.inspect(connection)
        assert inspector.has_table("tblalunos")
        assert "intalunoid" in {
            column["name"] for column in inspector.get_columns("tbleventosacesso")
        }
    engine.dispose()


def test_migration_aborts_when_student_cannot_be_preserved() -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        tables = _legacy_schema(connection)
        students = tables["students"]
        assert students is not None
        connection.execute(students.insert(), _legacy_student(1, "A100", ""))

        with pytest.raises(RuntimeError, match="no usable full name"):
            _migration(connection).upgrade()

        assert sa.inspect(connection).has_table("tblalunos")
    engine.dispose()


def test_migration_rejects_an_unexpected_legacy_dependency() -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "CREATE TABLE tblinesperada ("
                "id INTEGER PRIMARY KEY, intalunoid INTEGER)"
            )
        )

        with pytest.raises(RuntimeError, match="tblinesperada.intalunoid"):
            _migration(connection).upgrade()
    engine.dispose()


def test_migration_rejects_any_unexpected_foreign_key_to_tblalunos() -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        _legacy_schema(connection)
        connection.execute(
            sa.text(
                "CREATE TABLE tblinesperada ("
                "id INTEGER PRIMARY KEY, legacy_owner_id INTEGER, "
                "CONSTRAINT fk_inesperada_aluno FOREIGN KEY (legacy_owner_id) "
                "REFERENCES tblalunos(intalunoid))"
            )
        )

        with pytest.raises(RuntimeError, match="unexpected foreign keys"):
            _migration(connection).upgrade()
    engine.dispose()


@pytest.mark.parametrize("foreign_key_name", ["fk_evento_aluno_alternativa", None])
def test_sqlite_removes_equivalent_named_or_unnamed_legacy_foreign_key(
    foreign_key_name: str | None,
) -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        tables = _legacy_schema(
            connection, legacy_foreign_key_name=foreign_key_name
        )
        people = tables["people"]
        students = tables["students"]
        assert students is not None
        connection.execute(
            people.insert(),
            {
                "intpessoaid": 10,
                "strtipopessoa": "ALUNO",
                "strmatricula": "FK100",
                "strnomecompleto": "Aluno FK",
                "bolativo": True,
            },
        )
        connection.execute(students.insert(), _legacy_student(1, "FK100", "Aluno FK"))

        _migration(connection).upgrade()

        inspector = sa.inspect(connection)
        assert "tblalunos" not in inspector.get_table_names()
        assert "intalunoid" not in {
            column["name"] for column in inspector.get_columns("tbleventosacesso")
        }
    engine.dispose()


@pytest.mark.parametrize(
    ("include_students", "include_event_student_id"),
    [(True, False), (False, True), (False, False)],
)
def test_migration_resumes_from_partially_completed_schema(
    include_students: bool, include_event_student_id: bool,
) -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        tables = _legacy_schema(
            connection,
            include_students=include_students,
            include_event_student_id=include_event_student_id,
        )
        if include_students:
            students = tables["students"]
            assert students is not None
            connection.execute(
                students.insert(), _legacy_student(1, "PART100", "Aluno Parcial")
            )
        if include_event_student_id:
            connection.execute(
                tables["events"].insert(),
                {"inteventoacessoid": 1, "intalunoid": None, "intpessoaid": None},
            )

        migration = _migration(connection)
        migration.upgrade()
        migration.upgrade()

        inspector = sa.inspect(connection)
        assert "tblalunos" not in inspector.get_table_names()
        assert "intalunoid" not in {
            column["name"] for column in inspector.get_columns("tbleventosacesso")
        }
    engine.dispose()


def test_metadata_and_create_all_never_register_or_recreate_tblalunos() -> None:
    assert Student is Person
    assert "tblalunos" not in Base.metadata.tables
    assert "intalunoid" not in {column.name for column in Vehicle.__table__.columns}
    assert "intpessoaid" not in {column.name for column in Vehicle.__table__.columns}

    engine = sa.create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    assert "tblalunos" not in sa.inspect(engine).get_table_names()
    engine.dispose()


def test_students_api_reads_and_writes_only_aluno_people(
    client: TestClient, db_session: Session,
) -> None:
    headers = _headers(client)
    student_response = client.post(
        "/api/v1/students",
        json={"registration_number": "API610", "full_name": "Aluno API"},
        headers=headers,
    )
    assert student_response.status_code == 201
    employee_response = client.post(
        "/api/v1/people",
        json={
            "person_type": "FUNCIONARIO",
            "registration_number": "FUN610",
            "full_name": "Funcionario API",
        },
        headers=headers,
    )
    assert employee_response.status_code == 201

    response = client.get("/api/v1/students", headers=headers)
    assert response.status_code == 200
    assert [row["registration_number"] for row in response.json()] == ["API610"]
    student = db_session.get(Person, student_response.json()["id"])
    assert student is not None and student.person_type == "ALUNO"
    assert "tblalunos" not in sa.inspect(db_session.bind).get_table_names()
