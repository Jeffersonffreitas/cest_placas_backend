from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_student(
    client: TestClient,
    headers: dict[str, str],
    registration_number: str,
    full_name: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/students",
        json={
            "registration_number": registration_number,
            "full_name": full_name,
            "email": f"{registration_number}@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_vehicle(
    client: TestClient,
    headers: dict[str, str],
    student_id: int,
    plate: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "student_id": student_id,
            "plate": plate,
            "brand": "Fiat",
            "model": "Mobi",
            "color": "Branco",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _add_access_event(
    db_session: Session,
    *,
    plate_input: str,
    plate_normalized: str,
    status: str,
    created_at: datetime,
    source: str = "manual",
    student_id: int | None = None,
    vehicle_id: int | None = None,
) -> AccessEvent:
    access_event = AccessEvent(
        plate_input=plate_input,
        plate_normalized=plate_normalized,
        source=source,
        status=status,
        student_id=student_id,
        vehicle_id=vehicle_id,
        created_at=created_at,
    )
    db_session.add(access_event)
    db_session.commit()
    db_session.refresh(access_event)
    return access_event


def test_access_events_list_requires_admin(client: TestClient) -> None:
    response = client.get("/api/v1/access-events")

    assert response.status_code == 401


def test_access_events_list_orders_by_newest_and_paginates(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    _add_access_event(
        db_session,
        plate_input="AAA1A11",
        plate_normalized="AAA1A11",
        status="not_found",
        created_at=datetime(2026, 5, 12, 8, 0, 0),
    )
    expected = _add_access_event(
        db_session,
        plate_input="BBB2B22",
        plate_normalized="BBB2B22",
        status="not_found",
        created_at=datetime(2026, 5, 12, 9, 0, 0),
    )
    _add_access_event(
        db_session,
        plate_input="CCC3C33",
        plate_normalized="CCC3C33",
        status="not_found",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
    )

    response = client.get("/api/v1/access-events?skip=1&limit=1", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == expected.id
    assert body[0]["plate_normalized"] == "BBB2B22"


def test_access_events_list_filters_plate_status_student_and_vehicle(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    first_student = _create_student(client, headers, "20260011", "Ana Costa")
    first_vehicle = _create_vehicle(client, headers, int(first_student["id"]), "abc-1d23")
    second_student = _create_student(client, headers, "20260012", "Bruno Lima")
    second_vehicle = _create_vehicle(client, headers, int(second_student["id"]), "def-2g34")

    first_event = _add_access_event(
        db_session,
        plate_input="abc-1d23",
        plate_normalized="ABC1D23",
        status="matched",
        student_id=int(first_student["id"]),
        vehicle_id=int(first_vehicle["id"]),
        created_at=datetime(2026, 5, 12, 8, 0, 0),
    )
    second_event = _add_access_event(
        db_session,
        plate_input="def-2g34",
        plate_normalized="DEF2G34",
        status="matched",
        student_id=int(second_student["id"]),
        vehicle_id=int(second_vehicle["id"]),
        created_at=datetime(2026, 5, 12, 9, 0, 0),
    )
    not_found_event = _add_access_event(
        db_session,
        plate_input="zzz-9z99",
        plate_normalized="ZZZ9Z99",
        status="not_found",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
    )

    plate_response = client.get("/api/v1/access-events?plate=abc-1d23", headers=headers)
    assert plate_response.status_code == 200
    assert [item["id"] for item in plate_response.json()] == [first_event.id]
    assert plate_response.json()[0]["vehicle"]["id"] == first_vehicle["id"]
    assert plate_response.json()[0]["student"]["id"] == first_student["id"]

    status_response = client.get("/api/v1/access-events?status=not_found", headers=headers)
    assert status_response.status_code == 200
    assert [item["id"] for item in status_response.json()] == [not_found_event.id]

    student_response = client.get(
        f"/api/v1/access-events?student_id={first_student['id']}",
        headers=headers,
    )
    assert student_response.status_code == 200
    assert [item["id"] for item in student_response.json()] == [first_event.id]

    vehicle_response = client.get(
        f"/api/v1/access-events?vehicle_id={second_vehicle['id']}",
        headers=headers,
    )
    assert vehicle_response.status_code == 200
    assert [item["id"] for item in vehicle_response.json()] == [second_event.id]


def test_access_events_list_filters_source_manual(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    expected = _add_access_event(
        db_session,
        plate_input="AAA1A11",
        plate_normalized="AAA1A11",
        source="manual",
        status="not_found",
        created_at=datetime(2026, 5, 12, 8, 0, 0),
    )
    _add_access_event(
        db_session,
        plate_input="BBB2B22",
        plate_normalized="BBB2B22",
        source="upload",
        status="not_found",
        created_at=datetime(2026, 5, 12, 9, 0, 0),
    )

    response = client.get("/api/v1/access-events?source=manual", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [expected.id]
    assert body[0]["source"] == "manual"


def test_access_events_list_filters_source_upload(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    _add_access_event(
        db_session,
        plate_input="AAA1A11",
        plate_normalized="AAA1A11",
        source="manual",
        status="not_found",
        created_at=datetime(2026, 5, 12, 8, 0, 0),
    )
    expected = _add_access_event(
        db_session,
        plate_input="BBB2B22",
        plate_normalized="BBB2B22",
        source="upload",
        status="not_found",
        created_at=datetime(2026, 5, 12, 9, 0, 0),
    )

    response = client.get("/api/v1/access-events?source=upload", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [expected.id]
    assert body[0]["source"] == "upload"


def test_access_events_list_filters_date_range_and_validates_range(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    _add_access_event(
        db_session,
        plate_input="AAA1A11",
        plate_normalized="AAA1A11",
        status="not_found",
        created_at=datetime(2026, 5, 12, 8, 0, 0),
    )
    expected = _add_access_event(
        db_session,
        plate_input="BBB2B22",
        plate_normalized="BBB2B22",
        status="not_found",
        created_at=datetime(2026, 5, 12, 9, 0, 0),
    )
    _add_access_event(
        db_session,
        plate_input="CCC3C33",
        plate_normalized="CCC3C33",
        status="not_found",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
    )

    response = client.get(
        "/api/v1/access-events"
        "?date_from=2026-05-12T08:30:00"
        "&date_to=2026-05-12T09:30:00",
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [expected.id]

    invalid_response = client.get(
        "/api/v1/access-events"
        "?date_from=2026-05-12T10:00:00"
        "&date_to=2026-05-12T09:00:00",
        headers=headers,
    )
    assert invalid_response.status_code == 400
    assert invalid_response.json()["error"]["code"] == "invalid_date_range"


def test_access_events_list_rejects_invalid_status(client: TestClient) -> None:
    headers = _admin_headers(client)

    response = client.get("/api/v1/access-events?status=pending", headers=headers)

    assert response.status_code == 422


def test_access_events_list_rejects_invalid_plate_filter(client: TestClient) -> None:
    headers = _admin_headers(client)

    response = client.get("/api/v1/access-events?plate=ABC", headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_plate"


def test_access_events_list_without_filter_returns_event_details(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    student = _create_student(client, headers, "20260021", "Carla Souza")
    vehicle = _create_vehicle(client, headers, int(student["id"]), "ghi-3j45")
    expected = _add_access_event(
        db_session,
        plate_input="ghi-3j45",
        plate_normalized="GHI3J45",
        source="manual",
        status="matched",
        student_id=int(student["id"]),
        vehicle_id=int(vehicle["id"]),
        created_at=datetime(2026, 5, 13, 8, 0, 0),
    )

    response = client.get("/api/v1/access-events", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == expected.id
    assert body[0]["plate_input"] == "ghi-3j45"
    assert body[0]["plate_normalized"] == "GHI3J45"
    assert body[0]["source"] == "manual"
    assert body[0]["status"] == "matched"
    assert body[0]["created_at"] == "2026-05-13T08:00:00"
    assert body[0]["vehicle"]["id"] == vehicle["id"]
    assert body[0]["student"]["id"] == student["id"]


def test_access_events_list_rejects_invalid_source(client: TestClient) -> None:
    headers = _admin_headers(client)

    response = client.get("/api/v1/access-events?source=camera", headers=headers)

    assert response.status_code == 422


def test_access_events_summary_requires_admin(client: TestClient) -> None:
    response = client.get("/api/v1/access-events/summary")

    assert response.status_code == 401


def test_access_events_summary_returns_filtered_totals(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _admin_headers(client)
    _add_access_event(
        db_session,
        plate_input="AAA1A11",
        plate_normalized="AAA1A11",
        source="manual",
        status="matched",
        created_at=datetime(2026, 5, 12, 8, 0, 0),
    )
    _add_access_event(
        db_session,
        plate_input="BBB2B22",
        plate_normalized="BBB2B22",
        source="upload",
        status="not_found",
        created_at=datetime(2026, 5, 12, 9, 0, 0),
    )
    _add_access_event(
        db_session,
        plate_input="CCC3C33",
        plate_normalized="CCC3C33",
        source="upload",
        status="matched",
        created_at=datetime(2026, 5, 12, 10, 0, 0),
    )
    _add_access_event(
        db_session,
        plate_input="DDD4D44",
        plate_normalized="DDD4D44",
        source="manual",
        status="not_found",
        created_at=datetime(2026, 5, 12, 11, 0, 0),
    )

    response = client.get(
        "/api/v1/access-events/summary"
        "?source=upload"
        "&date_from=2026-05-12T08:30:00"
        "&date_to=2026-05-12T10:30:00",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "total_events": 2,
        "total_matched": 1,
        "total_not_found": 1,
        "total_manual": 0,
        "total_upload": 2,
        "total_by_status": {"matched": 1, "not_found": 1},
        "total_by_source": {"manual": 0, "upload": 2},
        "period": {
            "date_from": "2026-05-12T08:30:00",
            "date_to": "2026-05-12T10:30:00",
        },
    }

    status_response = client.get(
        "/api/v1/access-events/summary?status=matched",
        headers=headers,
    )

    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["total_events"] == 2
    assert status_body["total_by_status"] == {"matched": 2, "not_found": 0}
    assert status_body["total_by_source"] == {"manual": 1, "upload": 1}
    assert status_body["period"] is None
