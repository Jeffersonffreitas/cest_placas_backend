from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.domain import Domain
from app.models.person import Person
from app.models.vehicle import Vehicle


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _today(hour: int) -> datetime:
    return datetime.now(UTC).replace(
        hour=hour, minute=0, second=0, microsecond=0, tzinfo=None
    )


def _seed_operational_events(db: Session) -> dict[str, object]:
    people = {
        person_type: Person(
            person_type=person_type,
            registration_number=f"REG-{index}",
            full_name=f"Pessoa {person_type}",
            is_active=True,
        )
        for index, person_type in enumerate(
            ("ALUNO", "FUNCIONARIO", "VISITANTE"), start=1
        )
    }
    vehicles = [
        Vehicle(plate=plate, is_active=True)
        for plate in ("AAA1A11", "BBB2B22", "CCC3C33")
    ]
    action = Domain(
        type="ACAO_ACESSO", code="ENTRADA", name="Entrada", is_active=True
    )
    origin = Domain(
        type="ORIGEM_ACESSO", code="GUARITA", name="Guarita", is_active=True
    )
    db.add_all([*people.values(), *vehicles, action, origin])
    db.flush()

    events = [
        AccessEvent(
            vehicle_id=vehicles[0].id,
            person_id=people["ALUNO"].id,
            action_id=action.id,
            origin_id=origin.id,
            status="ACESSO_LIBERADO",
            plate_input="aaa-1a11",
            plate_normalized="AAA1A11",
            origin="manual",
            created_at=_today(8),
        ),
        AccessEvent(
            vehicle_id=vehicles[0].id,
            person_id=people["ALUNO"].id,
            action_id=action.id,
            origin_id=origin.id,
            status="ACESSO_LIBERADO",
            plate_input="AAA1A11",
            plate_normalized="AAA1A11",
            origin="manual",
            created_at=_today(9),
        ),
        AccessEvent(
            vehicle_id=vehicles[1].id,
            person_id=people["FUNCIONARIO"].id,
            action_id=action.id,
            origin_id=origin.id,
            status="ACESSO_LIBERADO",
            plate_input="BBB2B22",
            plate_normalized="BBB2B22",
            origin="upload",
            created_at=_today(10),
        ),
        AccessEvent(
            vehicle_id=vehicles[2].id,
            person_id=people["VISITANTE"].id,
            action_id=action.id,
            origin_id=origin.id,
            status="PESSOA_NAO_VINCULADA",
            plate_input="CCC3C33",
            plate_normalized="CCC3C33",
            origin="manual",
            created_at=_today(11),
        ),
        AccessEvent(
            status="VEICULO_NAO_CADASTRADO",
            plate_input="DDD4D44",
            plate_normalized="DDD4D44",
            origin="manual",
            created_at=_today(8) - timedelta(days=1),
        ),
    ]
    db.add_all(events)
    db.commit()
    for event in events:
        db.refresh(event)
    return {
        "people": people,
        "vehicles": vehicles,
        "action": action,
        "origin": origin,
        "events": events,
    }


@pytest.mark.parametrize(
    "path",
    (
        "/api/v1/access-events",
        "/api/v1/access-events/summary",
        "/api/v1/access-events/recent",
        "/api/v1/access-events/stats",
    ),
)
def test_operational_queries_require_authentication(
    client: TestClient, path: str
) -> None:
    assert client.get(path).status_code == 401


def test_list_filters_and_returns_operational_details(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_operational_events(db_session)
    headers = _admin_headers(client)
    people = seeded["people"]
    vehicles = seeded["vehicles"]

    response = client.get("/api/v1/access-events", headers=headers)
    assert response.status_code == 200
    assert [item["plate_normalized"] for item in response.json()[:4]] == [
        "CCC3C33",
        "BBB2B22",
        "AAA1A11",
        "AAA1A11",
    ]
    assert response.json()[0]["person_type"] == "VISITANTE"
    assert response.json()[0]["action"]["code"] == "ENTRADA"
    assert response.json()[0]["origin_domain"]["code"] == "GUARITA"

    cases = (
        ("plate=aaa-1a11", 2),
        ("status=PESSOA_NAO_VINCULADA", 1),
        (f"person_id={people['FUNCIONARIO'].id}", 1),
        (f"vehicle_id={vehicles[1].id}", 1),
        ("person_type=ALUNO", 2),
        ("person_type=FUNCIONARIO", 1),
        ("person_type=VISITANTE", 1),
        (f"date_from={_today(10).isoformat()}", 2),
        (f"date_to={_today(9).isoformat()}", 3),
    )
    for query, expected_count in cases:
        filtered = client.get(f"/api/v1/access-events?{query}", headers=headers)
        assert filtered.status_code == 200, query
        assert len(filtered.json()) == expected_count, query


def test_list_validates_dates_pagination_and_person_type(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    invalid_range = client.get(
        "/api/v1/access-events?date_from=2026-05-13T00:00:00"
        "&date_to=2026-05-12T00:00:00",
        headers=headers,
    )
    assert invalid_range.status_code == 400
    assert invalid_range.json()["error"]["code"] == "invalid_date_range"
    assert client.get(
        "/api/v1/access-events?limit=0", headers=headers
    ).status_code == 422
    assert client.get(
        "/api/v1/access-events?limit=101", headers=headers
    ).status_code == 422
    assert client.get(
        "/api/v1/access-events?skip=-1", headers=headers
    ).status_code == 422
    assert client.get(
        "/api/v1/access-events?person_type=OUTRO", headers=headers
    ).status_code == 422


def test_recent_orders_limits_and_filters(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_operational_events(db_session)
    headers = _admin_headers(client)
    origin = seeded["origin"]

    recent = client.get("/api/v1/access-events/recent?limit=2", headers=headers)
    assert recent.status_code == 200
    assert [item["plate_normalized"] for item in recent.json()] == [
        "CCC3C33",
        "BBB2B22",
    ]
    assert len(recent.json()) == 2

    granted = client.get(
        "/api/v1/access-events/recent?status=ACESSO_LIBERADO", headers=headers
    )
    assert granted.status_code == 200
    assert len(granted.json()) == 3
    assert all(item["status"] == "ACESSO_LIBERADO" for item in granted.json())

    employees = client.get(
        "/api/v1/access-events/recent?person_type=FUNCIONARIO", headers=headers
    )
    assert employees.status_code == 200
    assert [item["person_type"] for item in employees.json()] == ["FUNCIONARIO"]

    by_origin = client.get(
        f"/api/v1/access-events/recent?origin_id={origin.id}", headers=headers
    )
    assert by_origin.status_code == 200
    assert len(by_origin.json()) == 4
    assert client.get(
        "/api/v1/access-events/recent?limit=0", headers=headers
    ).status_code == 422


def test_stats_without_events(client: TestClient) -> None:
    response = client.get("/api/v1/access-events/stats", headers=_admin_headers(client))
    assert response.status_code == 200
    assert response.json() == {
        "total_today": 0,
        "access_granted_today": 0,
        "unresolved_today": 0,
        "unique_vehicles_today": 0,
        "unique_people_today": 0,
        "students_today": 0,
        "employees_today": 0,
        "visitors_today": 0,
    }


def test_stats_counts_today_distinct_entities_and_person_types(
    client: TestClient, db_session: Session
) -> None:
    _seed_operational_events(db_session)
    response = client.get("/api/v1/access-events/stats", headers=_admin_headers(client))
    assert response.status_code == 200
    assert response.json() == {
        "total_today": 4,
        "access_granted_today": 3,
        "unresolved_today": 1,
        "unique_vehicles_today": 3,
        "unique_people_today": 3,
        "students_today": 2,
        "employees_today": 1,
        "visitors_today": 1,
    }


def test_summary_keeps_legacy_fields_and_adds_operational_groups(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_operational_events(db_session)
    headers = _admin_headers(client)
    summary = client.get(
        "/api/v1/access-events/summary?date_from=" + _today(0).isoformat(),
        headers=headers,
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["total"] == body["total_events"] == 4
    assert body["total_access_granted"] == 3
    assert body["total_person_not_linked"] == 1
    assert body["total_vehicle_not_registered"] == 0
    assert body["by_status"] == {
        "ACESSO_LIBERADO": 3,
        "PESSOA_NAO_VINCULADA": 1,
    }
    assert body["by_origin"] == {"GUARITA": 4}
    assert body["by_action"] == {"ENTRADA": 4}
    assert body["by_person_type"] == {
        "ALUNO": 2,
        "FUNCIONARIO": 1,
        "VISITANTE": 1,
    }

    filtered = client.get(
        "/api/v1/access-events/summary"
        f"?plate=BBB2B22&person_type=FUNCIONARIO"
        f"&origin_id={seeded['origin'].id}",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total_events"] == 1


def test_summary_rejects_inverted_period(client: TestClient) -> None:
    response = client.get(
        "/api/v1/access-events/summary?date_from=2026-05-13T00:00:00"
        "&date_to=2026-05-12T00:00:00",
        headers=_admin_headers(client),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_date_range"
