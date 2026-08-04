import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.student import Student


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "change_me"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_person(
    client: TestClient, headers: dict[str, str], *, person_type: str,
    registration_number: str, full_name: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/people",
        json={
            "person_type": person_type,
            "registration_number": registration_number,
            "full_name": full_name,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_people_crud_filters_lookup_update_and_deactivate(client: TestClient) -> None:
    headers = _headers(client)
    student = _create_person(
        client, headers, person_type="ALUNO",
        registration_number="20261001", full_name="Ana Aluna",
    )
    employee = _create_person(
        client, headers, person_type="FUNCIONARIO",
        registration_number="F1001", full_name="Fabio Funcionario",
    )

    response = client.get("/api/v1/people", headers=headers)
    assert response.status_code == 200
    assert [person["id"] for person in response.json()] == [student["id"], employee["id"]]
    response = client.get(
        "/api/v1/people?registration_number=F1001&skip=0&limit=1", headers=headers
    )
    assert response.status_code == 200
    assert [person["id"] for person in response.json()] == [employee["id"]]
    assert client.get("/api/v1/people?limit=101", headers=headers).status_code == 422

    for person_type, expected_id in (("ALUNO", student["id"]), ("FUNCIONARIO", employee["id"])):
        response = client.get(
            f"/api/v1/people?person_type={person_type}", headers=headers
        )
        assert response.status_code == 200
        assert [person["id"] for person in response.json()] == [expected_id]

    response = client.get(f"/api/v1/people/{student['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["person_type"] == "ALUNO"

    response = client.get(
        "/api/v1/people/by-registration/F1001", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == employee["id"]

    response = client.put(
        f"/api/v1/people/{employee['id']}",
        json={"full_name": "Fabio Atualizado", "phone": "85999990000"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Fabio Atualizado"

    response = client.delete(f"/api/v1/people/{student['id']}", headers=headers)
    assert response.status_code == 204
    response = client.get("/api/v1/people?active=false", headers=headers)
    assert response.status_code == 200
    assert [person["id"] for person in response.json()] == [student["id"]]


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"person_type": "VISITANTE", "registration_number": "V1", "full_name": "Visitante"}, 422),
        ({"person_type": "ALUNO", "registration_number": "", "full_name": "Sem Matricula"}, 422),
        ({"person_type": "ALUNO", "registration_number": "A1", "full_name": ""}, 422),
    ],
)
def test_person_rejects_invalid_required_data(
    client: TestClient, payload: dict[str, object], expected_status: int,
) -> None:
    response = client.post("/api/v1/people", json=payload, headers=_headers(client))
    assert response.status_code == expected_status


def test_person_rejects_duplicate_active_registration(client: TestClient) -> None:
    headers = _headers(client)
    _create_person(
        client, headers, person_type="ALUNO",
        registration_number="DUP100", full_name="Primeira Pessoa",
    )
    response = client.post(
        "/api/v1/people",
        json={
            "person_type": "FUNCIONARIO",
            "registration_number": "DUP100",
            "full_name": "Segunda Pessoa",
        },
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "person_registration_number_conflict"


def test_person_validates_active_course_domain(client: TestClient) -> None:
    headers = _headers(client)
    response = client.post(
        "/api/v1/people",
        json={
            "person_type": "ALUNO", "registration_number": "C100",
            "full_name": "Curso Invalido", "course_id": 999999,
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_course_id"

    domain_response = client.post(
        "/api/v1/domains",
        json={"type": "CURSO", "name": "Curso Inativo", "is_active": False},
        headers=headers,
    )
    assert domain_response.status_code == 201
    response = client.post(
        "/api/v1/people",
        json={
            "person_type": "ALUNO", "registration_number": "C101",
            "full_name": "Curso Inativo", "course_id": domain_response.json()["id"],
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_course_id"


def test_people_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/people").status_code == 401
    assert client.get("/api/v1/people/1").status_code == 401
    assert client.get("/api/v1/people/by-registration/A1").status_code == 401
    assert client.post(
        "/api/v1/people",
        json={"person_type": "ALUNO", "registration_number": "A1", "full_name": "Ana"},
    ).status_code == 401
    assert client.put("/api/v1/people/1", json={"full_name": "Ana"}).status_code == 401
    assert client.delete("/api/v1/people/1").status_code == 401


def test_students_and_vehicles_endpoints_remain_compatible(client: TestClient) -> None:
    headers = _headers(client)
    student_response = client.post(
        "/api/v1/students",
        json={"registration_number": "LEG100", "full_name": "Aluno Legado"},
        headers=headers,
    )
    assert student_response.status_code == 201
    vehicle_response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_response.json()["id"], "plate": "LEG1A00",
            "brand": "Fiat", "model": "Mobi", "color": "Branco",
        },
        headers=headers,
    )
    assert vehicle_response.status_code == 201
    assert vehicle_response.json()["student_id"] == student_response.json()["id"]


def test_student_copy_is_idempotent_and_preserves_legacy_student(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    student = Student(
        registration_number="MIG100", full_name="Aluno Migrado",
        email="migrado@example.com", phone="85999999999", is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    context = MigrationContext.configure(db_session.connection())
    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "0010_create_people.py"
    spec = importlib.util.spec_from_file_location("migration_0010_create_people", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration, "op", Operations(context))

    migration._copy_students()
    migration._copy_students()

    people = list(
        db_session.scalars(
            select(Person).where(Person.registration_number == "MIG100")
        ).all()
    )
    assert len(people) == 1
    assert people[0].person_type == "ALUNO"
    assert people[0].full_name == "Aluno Migrado"
    assert db_session.get(Student, student.id) is not None
