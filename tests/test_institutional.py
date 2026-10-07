import importlib.util
from datetime import datetime
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import (
    Boolean,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    inspect,
    select,
)
from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.vehicle import Vehicle


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "change_me"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_institutional_lookup_returns_student_course_and_coordination(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/institutional/people/20260001", headers=_headers(client)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["registration"] == "20260001"
    assert body["person_type"] == "ALUNO"
    assert body["active"] is True
    assert body["course"] == {
        "name": "Análise e Desenvolvimento de Sistemas",
        "code": "ADS",
    }
    assert body["coordination"] == {
        "name": "Coordenação de Tecnologia",
        "acronym": "CTI",
    }


def test_institutional_lookup_returns_employee_without_course(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/institutional/people/func0001", headers=_headers(client)
    )

    assert response.status_code == 200
    assert response.json()["person_type"] == "FUNCIONARIO"
    assert response.json()["course"] is None
    assert response.json()["coordination"] is None


def test_institutional_lookup_not_found_and_inactive_handling(
    client: TestClient,
) -> None:
    headers = _headers(client)
    missing = client.get(
        "/api/v1/institutional/people/NAO-EXISTE", headers=headers
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "institutional_person_not_found"

    inactive = client.get(
        "/api/v1/institutional/people/20260002", headers=headers
    )
    assert inactive.status_code == 200
    assert inactive.json()["active"] is False
    sync = client.post(
        "/api/v1/institutional/people/20260002/sync", headers=headers
    )
    assert sync.status_code == 409
    assert sync.json()["error"]["code"] == "institutional_person_inactive"


def test_sync_creates_updates_and_is_idempotent(
    client: TestClient, db_session: Session,
) -> None:
    headers = _headers(client)
    first = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=headers
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["person_type"] == "ALUNO"
    assert first_body["course_id"] is not None

    person = db_session.get(Person, first_body["id"])
    assert person is not None
    person.full_name = "Nome local desatualizado"
    person.email = "desatualizado@example.com"
    db_session.commit()

    second = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=headers
    )
    third = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=headers
    )
    assert second.status_code == 200
    assert third.status_code == 200
    assert second.json()["id"] == first_body["id"] == third.json()["id"]
    assert second.json()["full_name"] == "Aluno Institucional de Teste"
    count = db_session.scalar(
        select(func.count(Person.id)).where(Person.registration_number == "20260001")
    )
    assert count == 1


def test_sync_reuses_registration_case_insensitively(
    client: TestClient, db_session: Session,
) -> None:
    local_person = Person(
        person_type="FUNCIONARIO",
        registration_number="func0001",
        full_name="Funcionário local",
    )
    db_session.add(local_person)
    db_session.commit()
    person_id = local_person.id

    response = client.post(
        "/api/v1/institutional/people/FUNC0001/sync", headers=_headers(client)
    )

    assert response.status_code == 200
    assert response.json()["id"] == person_id
    assert response.json()["registration_number"] == "FUNC0001"
    count = db_session.scalar(
        select(func.count(Person.id)).where(
            func.upper(Person.registration_number) == "FUNC0001"
        )
    )
    assert count == 1


def test_sync_preserves_person_vehicle_link(
    client: TestClient, db_session: Session,
) -> None:
    headers = _headers(client)
    person_response = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=headers
    )
    assert person_response.status_code == 200
    person_id = person_response.json()["id"]
    vehicle = Vehicle(plate="INS1T23")
    db_session.add(vehicle)
    db_session.flush()
    link = PersonVehicle(person_id=person_id, vehicle_id=vehicle.id)
    db_session.add(link)
    db_session.commit()
    link_id = link.id

    response = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=headers
    )

    assert response.status_code == 200
    persisted_link = db_session.get(PersonVehicle, link_id)
    assert persisted_link is not None
    assert persisted_link.person_id == person_id
    assert persisted_link.is_active is True


def test_sync_does_not_convert_visitor_automatically(
    client: TestClient,
) -> None:
    headers = _headers(client)
    visitor = client.post(
        "/api/v1/people",
        json={
            "person_type": "VISITANTE",
            "registration_number": "FUNC0001",
            "full_name": "Visitante com registro coincidente",
        },
        headers=headers,
    )
    assert visitor.status_code == 201

    response = client.post(
        "/api/v1/institutional/people/FUNC0001/sync", headers=headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "institutional_visitor_conflict"


def test_courses_and_coordinations_lists_and_filters(client: TestClient) -> None:
    headers = _headers(client)
    assert client.post(
        "/api/v1/institutional/people/20260001/sync", headers=headers
    ).status_code == 200

    coordinations = client.get(
        "/api/v1/coordinations?active=true&name=tecnologia", headers=headers
    )
    assert coordinations.status_code == 200
    assert len(coordinations.json()) == 1
    coordination_id = coordinations.json()[0]["id"]

    courses = client.get(
        f"/api/v1/courses?active=true&coordination_id={coordination_id}&name=desenvolvimento",
        headers=headers,
    )
    assert courses.status_code == 200
    assert len(courses.json()) == 1
    assert courses.json()[0]["code"] == "ADS"
    assert courses.json()[0]["coordination"]["id"] == coordination_id
    assert client.get(
        f"/api/v1/courses?coordination_id={coordination_id + 999}", headers=headers
    ).json() == []


def test_institutional_course_and_coordination_endpoints_require_authentication(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/institutional/people/20260001").status_code == 401
    assert client.post(
        "/api/v1/institutional/people/20260001/sync"
    ).status_code == 401
    assert client.get("/api/v1/courses").status_code == 401
    assert client.get("/api/v1/coordinations").status_code == 401


def test_institutional_migration_is_idempotent_and_keeps_expected_schema(
    db_session: Session,
) -> None:
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "0016_institutional_people_courses.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_0016_institutional_people_courses", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    context = MigrationContext.configure(db_session.connection())
    migration.op = Operations(context)

    migration.upgrade()
    migration.upgrade()

    inspector = inspect(db_session.connection())
    assert {"tblcoordenacoes", "tblcursos", "tblpessoas"}.issubset(
        inspector.get_table_names()
    )
    registration = next(
        column
        for column in inspector.get_columns("tblpessoas")
        if column["name"] == "strmatricula"
    )
    assert registration["nullable"] is True
    course_foreign_keys = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys("tblpessoas")
        if foreign_key["constrained_columns"] == ["intcursoid"]
    ]
    assert course_foreign_keys[0]["referred_table"] == "tblcursos"


def test_institutional_migration_copies_legacy_course_on_sqlite() -> None:
    engine = create_engine("sqlite+pysqlite://")
    metadata = MetaData()
    domains = Table(
        "tbldominios",
        metadata,
        Column("intdominioid", Integer, primary_key=True),
        Column("strtipo", String(50), nullable=False),
        Column("strcodigo", String(100)),
        Column("strnome", String(255), nullable=False),
        Column("bolativo", Boolean, nullable=False),
    )
    people = Table(
        "tblpessoas",
        metadata,
        Column("intpessoaid", Integer, primary_key=True),
        Column("strtipopessoa", String(20), nullable=False),
        Column("strmatricula", String(50), nullable=False),
        Column("strnomecompleto", String(255), nullable=False),
        Column("stremail", String(255)),
        Column("strtelefone", String(20)),
        Column(
            "intcursoid",
            Integer,
            ForeignKey(
                "tbldominios.intdominioid",
                name="fk_tblpessoas_curso",
                ondelete="RESTRICT",
            ),
        ),
        Column("bolativo", Boolean, nullable=False),
        Column(
            "strmatriculaativa",
            String(50),
            Computed("CASE WHEN bolativo = 1 THEN strmatricula ELSE NULL END"),
        ),
        Column("dtacriacao", DateTime, nullable=False),
        Column("dtaatualizacao", DateTime, nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            domains.insert(),
            {
                "intdominioid": 15,
                "strtipo": "CURSO",
                "strcodigo": "DIR",
                "strnome": "Direito",
                "bolativo": True,
            },
        )
        connection.execute(
            people.insert(),
            {
                "intpessoaid": 1,
                "strtipopessoa": "ALUNO",
                "strmatricula": "LEG-CURSO-1",
                "strnomecompleto": "Aluno com curso legado",
                "intcursoid": 15,
                "bolativo": True,
                "dtacriacao": datetime(2026, 1, 1),
                "dtaatualizacao": datetime(2026, 1, 1),
            },
        )

        migration_path = (
            Path(__file__).parents[1]
            / "alembic"
            / "versions"
            / "0016_institutional_people_courses.py"
        )
        spec = importlib.util.spec_from_file_location(
            "migration_0016_legacy_sqlite", migration_path
        )
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()
        migration.upgrade()

        course = connection.execute(
            select(Table("tblcursos", MetaData(), autoload_with=connection))
        ).mappings().one()
        assert course["intcursoid"] == 15
        assert course["strcodigo"] == "DIR"
        inspector = inspect(connection)
        registration = next(
            column
            for column in inspector.get_columns("tblpessoas")
            if column["name"] == "strmatricula"
        )
        assert registration["nullable"] is True
        course_foreign_keys = [
            foreign_key
            for foreign_key in inspector.get_foreign_keys("tblpessoas")
            if foreign_key["constrained_columns"] == ["intcursoid"]
        ]
        assert course_foreign_keys[0]["referred_table"] == "tblcursos"
    engine.dispose()
