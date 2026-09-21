import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_domain(
    client: TestClient, headers: dict[str, str], domain_type: str, code: str
) -> dict[str, object]:
    response = client.post(
        "/api/v1/domains",
        json={"type": domain_type, "code": code, "name": code, "is_active": True},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_person(
    client: TestClient,
    headers: dict[str, str],
    person_type: str,
    registration: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/people",
        json={
            "person_type": person_type,
            "registration_number": registration,
            "full_name": f"Pessoa {person_type}",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_vehicle(
    client: TestClient, headers: dict[str, str], plate: str
) -> dict[str, object]:
    response = client.post(
        "/api/v1/vehicles",
        json={"plate": plate, "brand": "Marca", "model": "Modelo"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _link(
    client: TestClient, headers: dict[str, str], person_id: int, vehicle_id: int
) -> None:
    response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": person_id, "vehicle_id": vehicle_id},
        headers=headers,
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("person_type", "plate", "registration"),
    [
        ("ALUNO", "AAA1A11", "A-6401"),
        ("FUNCIONARIO", "BBB2B22", "F-6401"),
        ("VISITANTE", "CCC3C33", "V-6401"),
    ],
)
def test_create_event_resolves_all_person_types(
    client: TestClient,
    person_type: str,
    plate: str,
    registration: str,
) -> None:
    headers = _admin_headers(client)
    person = _create_person(client, headers, person_type, registration)
    vehicle = _create_vehicle(client, headers, plate)
    _link(client, headers, int(person["id"]), int(vehicle["id"]))
    action = _create_domain(client, headers, "ACAO_ACESSO", "ENTRADA")
    origin = _create_domain(client, headers, "ORIGEM_ACESSO", "PORTAO_PRINCIPAL")

    response = client.post(
        "/api/v1/access-events",
        json={
            "plate": plate,
            "action_id": action["id"],
            "origin_id": origin["id"],
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ACESSO_LIBERADO"
    assert body["vehicle_id"] == vehicle["id"]
    assert body["person_id"] == person["id"]
    assert body["person"]["person_type"] == person_type
    assert body["action_id"] == action["id"]
    assert body["origin_id"] == origin["id"]
    assert body["origin"] == "PORTAO_PRINCIPAL"
    if person_type == "ALUNO":
        assert body["student"]["id"] == person["id"]
    else:
        assert body["student"] is None

    detail = client.get(f"/api/v1/access-events/{body['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["person_id"] == person["id"]
    person_filter = client.get(
        f"/api/v1/access-events?person_id={person['id']}", headers=headers
    )
    assert person_filter.status_code == 200
    assert [item["id"] for item in person_filter.json()] == [body["id"]]


def test_event_resolution_statuses_filters_summary_and_no_student_fk(
    client: TestClient, db_session: Session
) -> None:
    headers = _admin_headers(client)
    action = _create_domain(client, headers, "ACAO_ACESSO", "TENTATIVA")
    origin = _create_domain(client, headers, "ORIGEM_ACESSO", "GUARITA")
    vehicle = _create_vehicle(client, headers, "DDD4D44")

    no_person = client.post(
        "/api/v1/access-events",
        json={"plate": "ddd-4d44", "action_id": action["id"], "origin_id": origin["id"]},
        headers=headers,
    )
    unknown = client.post(
        "/api/v1/access-events",
        json={"plate": "ZZZ9Z99", "action_id": action["id"], "origin_id": origin["id"]},
        headers=headers,
    )
    assert no_person.status_code == 201
    assert no_person.json()["status"] == "PESSOA_NAO_VINCULADA"
    assert no_person.json()["vehicle_id"] == vehicle["id"]
    assert no_person.json()["person_id"] is None
    assert unknown.status_code == 201
    assert unknown.json()["status"] == "VEICULO_NAO_CADASTRADO"

    event_id = no_person.json()["id"]
    filters = {
        "plate": "DDD4D44",
        "vehicle_id": vehicle["id"],
        "action_id": action["id"],
        "origin_id": origin["id"],
        "status": "PESSOA_NAO_VINCULADA",
        "origin": "GUARITA",
    }
    for key, value in filters.items():
        response = client.get(f"/api/v1/access-events?{key}={value}", headers=headers)
        assert response.status_code == 200
        returned_ids = [item["id"] for item in response.json()]
        if key in {"action_id", "origin_id", "origin"}:
            assert returned_ids == [unknown.json()["id"], event_id]
        else:
            assert returned_ids == [event_id]

    summary = client.get("/api/v1/access-events/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total"] == 2
    assert summary.json()["by_status"] == {
        "PESSOA_NAO_VINCULADA": 1,
        "VEICULO_NAO_CADASTRADO": 1,
    }
    assert summary.json()["by_action"] == {"TENTATIVA": 2}
    assert summary.json()["by_origin"] == {"GUARITA": 2}

    assert "intalunoid" not in {
        column["name"]
        for column in inspect(db_session.bind).get_columns(AccessEvent.__tablename__)
    }


def test_access_event_validates_auth_limit_domains_and_ids(client: TestClient) -> None:
    headers = _admin_headers(client)
    wrong_domain = _create_domain(client, headers, "COR_VEICULO", "AZUL")

    assert client.post("/api/v1/access-events", json={"plate": "ABC1D23"}).status_code == 401
    assert client.get("/api/v1/access-events?limit=101", headers=headers).status_code == 422
    assert client.post(
        "/api/v1/access-events",
        json={"plate": "ABC1D23", "action_id": wrong_domain["id"]},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/api/v1/access-events",
        json={"plate": "ABC1D23", "vehicle_id": 999999},
        headers=headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/access-events",
        json={"plate": "ABC1D23", "person_id": 999999},
        headers=headers,
    ).status_code == 404
