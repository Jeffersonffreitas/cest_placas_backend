import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.person_vehicle import PersonVehicle
from app.models.student import Student
from app.models.vehicle import Vehicle


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "change_me"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _student(client: TestClient, headers: dict[str, str], number: str = "LEG001") -> int:
    response = client.post(
        "/api/v1/students",
        json={"registration_number": number, "full_name": f"Aluno {number}"},
        headers=headers,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _person(
    client: TestClient, headers: dict[str, str], number: str,
    person_type: str = "ALUNO",
) -> int:
    response = client.post(
        "/api/v1/people",
        json={
            "person_type": person_type,
            "registration_number": number,
            "full_name": f"Pessoa {number}",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _vehicle(
    client: TestClient, headers: dict[str, str], student_id: int, plate: str,
) -> int:
    response = client.post(
        "/api/v1/vehicles",
        json={"student_id": student_id, "plate": plate},
        headers=headers,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _link(
    client: TestClient, headers: dict[str, str], person_id: int, vehicle_id: int,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": person_id, "vehicle_id": vehicle_id},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_person_vehicle_crud_filters_and_logical_delete(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    person_id = _person(client, headers, "P001", "FUNCIONARIO")
    vehicle_id = _vehicle(client, headers, student_id, "ABC1D23")
    link = _link(client, headers, person_id, vehicle_id)
    assert link["person_id"] == person_id
    assert link["vehicle_id"] == vehicle_id
    assert link["is_active"] is True

    response = client.get("/api/v1/person-vehicles", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [link["id"]]
    assert client.get(
        "/api/v1/person-vehicles?limit=101", headers=headers
    ).status_code == 422
    for query in (f"person_id={person_id}", f"vehicle_id={vehicle_id}"):
        response = client.get(f"/api/v1/person-vehicles?{query}", headers=headers)
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [link["id"]]

    response = client.get(f"/api/v1/person-vehicles/{link['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == link["id"]

    response = client.delete(f"/api/v1/person-vehicles/{link['id']}", headers=headers)
    assert response.status_code == 204
    response = client.get("/api/v1/person-vehicles?active=false", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [link["id"]]


def test_person_vehicle_rejects_missing_entities_and_duplicate(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    person_id = _person(client, headers, "P002")
    vehicle_id = _vehicle(client, headers, student_id, "DEF2G34")

    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": 999999, "vehicle_id": vehicle_id}, headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "person_not_found"
    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": person_id, "vehicle_id": 999999}, headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "vehicle_not_found"

    _link(client, headers, person_id, vehicle_id)
    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": person_id, "vehicle_id": vehicle_id}, headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "person_vehicle_conflict"


def test_person_vehicle_rejects_inactive_entities(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    person_id = _person(client, headers, "P005")
    vehicle_id = _vehicle(client, headers, student_id, "STU7V89")

    assert client.delete(f"/api/v1/people/{person_id}", headers=headers).status_code == 204
    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": person_id, "vehicle_id": vehicle_id}, headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "person_inactive"

    active_person_id = _person(client, headers, "P006", "FUNCIONARIO")
    assert client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=headers).status_code == 204
    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": active_person_id, "vehicle_id": vehicle_id}, headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vehicle_inactive"


def test_many_to_many_and_navigation_endpoints(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers)
    first_person = _person(client, headers, "P003", "ALUNO")
    second_person = _person(client, headers, "P004", "FUNCIONARIO")
    first_vehicle = _vehicle(client, headers, student_id, "GHI3J45")
    second_vehicle = _vehicle(client, headers, student_id, "JKL4M56")

    _link(client, headers, first_person, first_vehicle)
    _link(client, headers, first_person, second_vehicle)
    _link(client, headers, second_person, first_vehicle)

    response = client.get(
        f"/api/v1/people/{first_person}/vehicles", headers=headers
    )
    assert response.status_code == 200
    assert [vehicle["id"] for vehicle in response.json()] == [first_vehicle, second_vehicle]

    response = client.get(
        f"/api/v1/vehicles/{first_vehicle}/owners", headers=headers
    )
    assert response.status_code == 200
    assert [person["id"] for person in response.json()] == [first_person, second_person]


def test_person_vehicle_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/person-vehicles").status_code == 401
    assert client.get("/api/v1/person-vehicles/1").status_code == 401
    assert client.post(
        "/api/v1/person-vehicles", json={"person_id": 1, "vehicle_id": 1}
    ).status_code == 401
    assert client.delete("/api/v1/person-vehicles/1").status_code == 401
    assert client.get("/api/v1/people/1/vehicles").status_code == 401
    assert client.get("/api/v1/vehicles/1/owners").status_code == 401


def test_old_students_vehicles_and_plate_lookup_still_work(client: TestClient) -> None:
    headers = _headers(client)
    student_id = _student(client, headers, "OLD001")
    vehicle_id = _vehicle(client, headers, student_id, "MNO5P67")
    assert client.get(f"/api/v1/students/{student_id}", headers=headers).status_code == 200
    response = client.get("/api/v1/vehicles/by-plate/mno-5p67", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == vehicle_id


def test_legacy_vehicle_links_are_copied_idempotently(db_session: Session) -> None:
    student = Student(registration_number="MIG200", full_name="Aluno Migrado")
    person = Person(
        person_type="ALUNO", registration_number="MIG200", full_name="Aluno Migrado"
    )
    db_session.add_all([student, person])
    db_session.flush()
    vehicle = Vehicle(student_id=student.id, plate="PQR6S78")
    db_session.add(vehicle)
    db_session.commit()

    migration_path = (
        Path(__file__).parents[1] / "alembic" / "versions"
        / "0011_create_person_vehicle.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_0011_create_person_vehicle", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    context = MigrationContext.configure(db_session.connection())
    migration.op = Operations(context)

    migration._copy_legacy_links()
    migration._copy_legacy_links()

    links = list(
        db_session.scalars(
            select(PersonVehicle).where(
                PersonVehicle.person_id == person.id,
                PersonVehicle.vehicle_id == vehicle.id,
            )
        ).all()
    )
    assert len(links) == 1
    assert links[0].is_active is True
