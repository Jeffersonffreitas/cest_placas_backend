from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.plate_read import PlateRead


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


def test_manual_read_links_plate_read_vehicle_person_domains_and_queries(
    client: TestClient, db_session: Session
) -> None:
    headers = _admin_headers(client)
    action = _create_domain(client, headers, "ACAO_ACESSO", "ENTRADA")
    origin = _create_domain(client, headers, "ORIGEM_ACESSO", "TESTE_MANUAL")
    person_response = client.post(
        "/api/v1/people",
        json={
            "person_type": "FUNCIONARIO",
            "registration_number": "F-6501",
            "full_name": "Pessoa Fase 6.5",
        },
        headers=headers,
    )
    assert person_response.status_code == 201
    person = person_response.json()
    vehicle = _create_vehicle(client, headers, "FAS6E50")
    link_response = client.post(
        "/api/v1/person-vehicles",
        json={"person_id": person["id"], "vehicle_id": vehicle["id"]},
        headers=headers,
    )
    assert link_response.status_code == 201

    response = client.post(
        "/api/v1/plates/read-manual", json={"plate": "fas-6e50"}, headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ACESSO_LIBERADO"
    assert body["success"] is True
    assert body["message"] == "Acesso liberado."
    assert body["operational_decision"] == "ACESSO_LIBERADO"
    assert body["vehicle"]["id"] == vehicle["id"]
    assert body["person"]["id"] == person["id"]
    assert body["person_type"] == "FUNCIONARIO"
    assert body["action"] == "ENTRADA"
    assert body["origin"] == "TESTE_MANUAL"
    assert body["access_event"]["id"] == body["access_event_id"]
    event = db_session.get(AccessEvent, body["access_event_id"])
    plate_read = db_session.get(PlateRead, body["plate_read_id"])
    assert event is not None and plate_read is not None
    assert event.plate_read_id == plate_read.id
    assert event.vehicle_id == vehicle["id"]
    assert event.person_id == person["id"]
    assert event.action_id == action["id"]
    assert event.origin_id == origin["id"]

    detail = client.get(f"/api/v1/access-events/{event.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["plate_read"]["id"] == plate_read.id
    assert detail.json()["vehicle"]["id"] == vehicle["id"]
    assert detail.json()["person"]["id"] == person["id"]
    listing = client.get("/api/v1/access-events", headers=headers)
    assert [item["id"] for item in listing.json()] == [event.id]
    summary = client.get("/api/v1/access-events/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["by_status"] == {"ACESSO_LIBERADO": 1}
    assert summary.json()["by_origin"] == {"TESTE_MANUAL": 1}
    assert summary.json()["total_manual"] == 1


def test_manual_read_registered_vehicle_without_person_creates_denied_event(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    vehicle = _create_vehicle(client, headers, "SEM1P23")

    response = client.post(
        "/api/v1/plates/read-manual", json={"plate": "SEM1P23"}, headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PESSOA_NAO_VINCULADA"
    assert body["operational_decision"] == "PESSOA_NAO_VINCULADA"
    assert body["vehicle"]["id"] == vehicle["id"]
    assert body["person"] is None
    assert isinstance(body["plate_read_id"], int)


def test_manual_read_unknown_vehicle_creates_event_linked_to_read(
    client: TestClient, db_session: Session
) -> None:
    headers = _admin_headers(client)

    response = client.post(
        "/api/v1/plates/read-manual", json={"plate": "ZZZ9Z99"}, headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "VEICULO_NAO_CADASTRADO"
    event = db_session.scalars(select(AccessEvent)).one()
    plate_read = db_session.scalars(select(PlateRead)).one()
    assert event.plate_read_id == plate_read.id == body["plate_read_id"]
    assert event.vehicle_id is None
    assert event.person_id is None
