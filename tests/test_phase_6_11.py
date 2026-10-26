from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.integrations.institutional import (
    InstitutionalCourse,
    InstitutionalPerson,
    InstitutionalProviderUnavailableError,
    LocalInstitutionalPersonProvider,
    get_institutional_person_provider,
)
from app.main import app
from app.models.coordination import Coordination
from app.models.course import Course
from app.models.person import Person
from app.models.student import Student
from app.models.vehicle import Vehicle
from app.services import plates as plate_service


class MutableInstitutionalProvider:
    def __init__(self, person: InstitutionalPerson | None) -> None:
        self.person = person

    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        del registration
        return self.person


class UnavailableInstitutionalProvider:
    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        del registration
        raise InstitutionalProviderUnavailableError("sensitive provider detail")


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def override_institutional_provider() -> Generator[
    Callable[[object], None], None, None
]:
    def apply(provider: object) -> None:
        app.dependency_overrides[get_institutional_person_provider] = lambda: provider

    try:
        yield apply
    finally:
        app.dependency_overrides.pop(get_institutional_person_provider, None)


def test_local_provider_returns_student_and_employee_without_external_dependency(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    student = client.get(
        "/api/v1/institutional/people/20260001", headers=admin_headers
    )
    employee = client.get(
        "/api/v1/institutional/people/func0001", headers=admin_headers
    )

    assert student.status_code == 200
    assert student.json()["person_type"] == "ALUNO"
    assert student.json()["phone"] == "85999990001"
    assert employee.status_code == 200
    assert employee.json()["person_type"] == "FUNCIONARIO"
    assert employee.json()["phone"] == "85999990002"
    assert isinstance(get_institutional_person_provider(), LocalInstitutionalPersonProvider)


def test_institutional_lookup_missing_registration_returns_404(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/institutional/people/NAO-EXISTE", headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "institutional_person_not_found"


def test_student_and_employee_sync_create_the_expected_person_types(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
) -> None:
    student = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=admin_headers
    )
    employee = client.post(
        "/api/v1/institutional/people/FUNC0001/sync", headers=admin_headers
    )

    assert student.status_code == employee.status_code == 200
    assert student.json()["person_type"] == "ALUNO"
    assert employee.json()["person_type"] == "FUNCIONARIO"
    assert student.json()["phone"] == "85999990001"
    assert employee.json()["phone"] == "85999990002"
    assert db_session.scalar(select(func.count(Person.id))) == 2


def test_sync_is_idempotent_updates_same_person_and_preserves_absent_fields(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
    override_institutional_provider: Callable[[object], None],
) -> None:
    first = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=admin_headers
    )
    assert first.status_code == 200
    person_id = first.json()["id"]
    course_id = first.json()["course_id"]

    provider = MutableInstitutionalProvider(
        InstitutionalPerson(
            registration="20260001",
            full_name="Aluno Institucional Atualizado",
            person_type="ESTUDANTE",  # type: ignore[arg-type]
            active=True,
        )
    )
    override_institutional_provider(provider)
    second = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=admin_headers
    )
    third = client.post(
        "/api/v1/institutional/people/20260001/sync", headers=admin_headers
    )

    assert second.status_code == third.status_code == 200
    assert second.json()["id"] == third.json()["id"] == person_id
    assert second.json()["full_name"] == "Aluno Institucional Atualizado"
    assert second.json()["email"] == "aluno.teste@cest.edu.br"
    assert second.json()["phone"] == "85999990001"
    assert second.json()["course_id"] == course_id
    assert db_session.scalar(
        select(func.count(Person.id)).where(
            func.upper(Person.registration_number) == "20260001"
        )
    ) == 1


def test_institutional_type_change_reuses_registration_instead_of_duplicating(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
    override_institutional_provider: Callable[[object], None],
) -> None:
    provider = MutableInstitutionalProvider(
        InstitutionalPerson(
            registration="REG-TIPO-1",
            full_name="Pessoa Institucional",
            person_type="ALUNO",
            active=True,
        )
    )
    override_institutional_provider(provider)
    first = client.post(
        "/api/v1/institutional/people/REG-TIPO-1/sync", headers=admin_headers
    )
    provider.person = InstitutionalPerson(
        registration="REG-TIPO-1",
        full_name="Pessoa Institucional",
        person_type="COLABORADOR",  # type: ignore[arg-type]
        active=True,
    )
    second = client.post(
        "/api/v1/institutional/people/REG-TIPO-1/sync", headers=admin_headers
    )

    assert first.status_code == second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["person_type"] == "FUNCIONARIO"
    assert db_session.scalar(
        select(func.count(Person.id)).where(
            Person.registration_number == "REG-TIPO-1"
        )
    ) == 1


def test_provider_unavailable_returns_controlled_503_without_internal_detail(
    client: TestClient,
    admin_headers: dict[str, str],
    override_institutional_provider: Callable[[object], None],
) -> None:
    override_institutional_provider(UnavailableInstitutionalProvider())

    for method, path in (
        ("get", "/api/v1/institutional/people/REG-1"),
        ("post", "/api/v1/institutional/people/REG-1/sync"),
    ):
        response = client.request(method, path, headers=admin_headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "institutional_provider_unavailable"
        assert "sensitive provider detail" not in response.text


def test_invalid_institutional_type_is_rejected_without_persistence(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
    override_institutional_provider: Callable[[object], None],
) -> None:
    provider = MutableInstitutionalProvider(
        InstitutionalPerson(
            registration="TIPO-INVALIDO",
            full_name="Tipo Invalido",
            person_type="VISITANTE",  # type: ignore[arg-type]
            active=True,
        )
    )
    override_institutional_provider(provider)

    response = client.post(
        "/api/v1/institutional/people/TIPO-INVALIDO/sync", headers=admin_headers
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "institutional_person_type_invalid"
    assert db_session.scalar(select(func.count(Person.id))) == 0


def test_incomplete_provider_data_is_rejected_without_persistence(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
    override_institutional_provider: Callable[[object], None],
) -> None:
    provider = MutableInstitutionalProvider(
        InstitutionalPerson(
            registration="INCOMPLETO-1",
            full_name=" ",
            person_type="ALUNO",
            active=True,
        )
    )
    override_institutional_provider(provider)

    response = client.post(
        "/api/v1/institutional/people/INCOMPLETO-1/sync", headers=admin_headers
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "institutional_provider_invalid_response"
    assert db_session.scalar(select(func.count(Person.id))) == 0


def test_course_without_coordination_does_not_invent_academic_data(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
    override_institutional_provider: Callable[[object], None],
) -> None:
    provider = MutableInstitutionalProvider(
        InstitutionalPerson(
            registration="SEM-COORD-1",
            full_name="Aluno sem coordenacao informada",
            person_type="ALUNO",
            active=True,
            course=InstitutionalCourse(name="Curso real sem coordenacao", code="CRSC"),
        )
    )
    override_institutional_provider(provider)

    response = client.post(
        "/api/v1/institutional/people/SEM-COORD-1/sync", headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["course_id"] is None
    assert db_session.scalar(select(func.count(Course.id))) == 0
    assert db_session.scalar(select(func.count(Coordination.id))) == 0


def test_courses_and_coordinations_are_synchronized_idempotently(
    client: TestClient,
    db_session: Session,
    admin_headers: dict[str, str],
) -> None:
    for _ in range(2):
        response = client.post(
            "/api/v1/institutional/people/20260001/sync", headers=admin_headers
        )
        assert response.status_code == 200

    assert db_session.scalar(select(func.count(Course.id))) == 1
    assert db_session.scalar(select(func.count(Coordination.id))) == 1
    assert len(client.get("/api/v1/courses", headers=admin_headers).json()) == 1
    assert len(client.get("/api/v1/coordinations", headers=admin_headers).json()) == 1


def test_visitor_and_operational_endpoints_continue_working(
    client: TestClient,
    admin_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plate_service, "PLATE_READ_UPLOAD_DIR", tmp_path / "uploads")
    me = client.get("/api/v1/auth/me", headers=admin_headers)
    assert me.status_code == 200

    visitor = client.post(
        "/api/v1/people",
        json={"person_type": "VISITANTE", "full_name": "Visitante Local"},
        headers=admin_headers,
    )
    assert visitor.status_code == 201
    student = client.post(
        "/api/v1/students",
        json={"registration_number": "FASE611-ALUNO", "full_name": "Aluno Local"},
        headers=admin_headers,
    )
    assert student.status_code == 201

    vehicle = client.post(
        "/api/v1/vehicles",
        json={"plate": "FSX6B11", "person_id": visitor.json()["id"]},
        headers=admin_headers,
    )
    assert vehicle.status_code == 201
    links = client.get(
        f"/api/v1/person-vehicles?person_id={visitor.json()['id']}",
        headers=admin_headers,
    )
    assert links.status_code == 200 and len(links.json()) == 1

    point = client.post(
        "/api/v1/access-points",
        json={"name": "Ponto Fase 6.11", "direction": "MISTO"},
        headers=admin_headers,
    )
    assert point.status_code == 201
    camera = client.post(
        "/api/v1/cameras",
        json={
            "access_point_id": point.json()["id"],
            "name": "Camera Fase 6.11",
            "code": "CAM-FASE-611",
        },
        headers=admin_headers,
    )
    assert camera.status_code == 201

    manual = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "FSX6B11", "camera_id": camera.json()["id"]},
        headers=admin_headers,
    )
    assert manual.status_code == 201
    assert manual.json()["person_type"] == "VISITANTE"

    image = client.post(
        "/api/v1/plates/read-image",
        data={"mock_plate": "FSX6B11", "camera_id": str(camera.json()["id"])},
        files={"file": ("fase-6-11.jpg", b"fake-image", "image/jpeg")},
        headers=admin_headers,
    )
    assert image.status_code == 201
    assert image.json()["person"]["id"] == visitor.json()["id"]

    assert client.get("/api/v1/access-events", headers=admin_headers).status_code == 200
    assert client.get(
        "/api/v1/access-events/recent", headers=admin_headers
    ).status_code == 200
    assert client.get(
        "/api/v1/access-events/summary", headers=admin_headers
    ).status_code == 200
    assert client.get(
        "/api/v1/access-events/stats", headers=admin_headers
    ).status_code == 200
    assert client.get("/api/v1/domains", headers=admin_headers).status_code == 200


def test_phase_6_10_schema_guards_remain_intact(db_session: Session) -> None:
    assert Student is Person
    assert "tblalunos" not in Base.metadata.tables
    assert "tblalunos" not in inspect(db_session.bind).get_table_names()
    vehicle_columns = {column.name for column in Vehicle.__table__.columns}
    assert "intalunoid" not in vehicle_columns
    assert "intpessoaid" not in vehicle_columns


def test_provider_configuration_defaults_to_local_and_accepts_rm_selection() -> None:
    assert Settings(_env_file=None).institutional_provider == "local"
    assert Settings(
        _env_file=None, INSTITUTIONAL_PROVIDER=" RM "
    ).institutional_provider == "rm"

