from pathlib import Path
import importlib.util

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.plate_read import PlateRead
from app.services import plates as plate_service


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "change_me"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _point(
    client: TestClient, headers: dict[str, str], name: str, direction: str
) -> dict[str, object]:
    response = client.post(
        "/api/v1/access-points",
        json={"name": name, "direction": direction},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _camera(
    client: TestClient, headers: dict[str, str], point_id: int, code: str
) -> dict[str, object]:
    response = client.post(
        "/api/v1/cameras",
        json={
            "access_point_id": point_id,
            "name": f"Camera {code}",
            "code": code,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_legacy_manual_read_without_location_remains_compatible(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "LEG1A23"},
        headers=_admin_headers(client),
    )
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["plate_read_id"], int)
    assert isinstance(body["access_event_id"], int)
    assert body["vehicle_side"] == "INDEFINIDO"
    assert body["camera"] is None
    assert body["access_point"] is None
    plate_read = db_session.get(PlateRead, body["plate_read_id"])
    event = db_session.get(AccessEvent, body["access_event_id"])
    assert plate_read is not None and plate_read.camera_id is None
    assert plate_read.vehicle_side == "INDEFINIDO"
    assert event is not None and event.access_point_id is None


@pytest.mark.parametrize("vehicle_side", ("FRONTAL", "TRASEIRA", "INDEFINIDO"))
def test_manual_read_with_logical_camera_persists_location_and_vehicle_side(
    client: TestClient, db_session: Session, vehicle_side: str
) -> None:
    headers = _admin_headers(client)
    point = _point(client, headers, "Portao Principal", "ENTRADA")
    camera = _camera(client, headers, int(point["id"]), f"CAM-{vehicle_side}")

    response = client.post(
        "/api/v1/plates/read-manual",
        json={
            "plate": "FRO1N23",
            "camera_id": camera["id"],
            "vehicle_side": vehicle_side,
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["vehicle_side"] == vehicle_side
    assert body["camera"] == {"id": camera["id"], "name": camera["name"]}
    assert body["access_point"] == {
        "id": point["id"],
        "name": point["name"],
        "direction": "ENTRADA",
    }
    plate_read = db_session.get(PlateRead, body["plate_read_id"])
    event = db_session.get(AccessEvent, body["access_event_id"])
    assert plate_read is not None and plate_read.camera_id == camera["id"]
    assert plate_read.vehicle_side == vehicle_side
    assert event is not None and event.access_point_id == point["id"]


def test_manual_read_rejects_invalid_vehicle_side(client: TestClient) -> None:
    response = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "ABC1D23", "vehicle_side": "LATERAL"},
        headers=_admin_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_inactive_camera_and_access_point_cannot_be_used_for_new_read(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    camera_point = _point(client, headers, "Ponto Camera", "ENTRADA")
    camera = _camera(client, headers, int(camera_point["id"]), "CAM-INATIVA")
    assert client.delete(
        f"/api/v1/cameras/{camera['id']}", headers=headers
    ).status_code == 204
    inactive_camera = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "INA1C23", "camera_id": camera["id"]},
        headers=headers,
    )
    assert inactive_camera.status_code == 422
    assert inactive_camera.json()["error"]["code"] == "inactive_camera"

    point = _point(client, headers, "Ponto Inativo", "SAIDA")
    assert client.delete(
        f"/api/v1/access-points/{point['id']}", headers=headers
    ).status_code == 204
    inactive_point = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "INA2P34", "access_point_id": point["id"]},
        headers=headers,
    )
    assert inactive_point.status_code == 422
    assert inactive_point.json()["error"]["code"] == "inactive_access_point"


def test_camera_and_access_point_mismatch_is_rejected(client: TestClient) -> None:
    headers = _admin_headers(client)
    first = _point(client, headers, "Primeiro", "ENTRADA")
    second = _point(client, headers, "Segundo", "SAIDA")
    camera = _camera(client, headers, int(first["id"]), "CAM-PRIMEIRO")
    response = client.post(
        "/api/v1/plates/read-manual",
        json={
            "plate": "MIS1M23",
            "camera_id": camera["id"],
            "access_point_id": second["id"],
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "camera_access_point_mismatch"


def test_access_event_queries_filter_by_access_point_and_camera_without_duplicates(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    first = _point(client, headers, "Entrada", "ENTRADA")
    second = _point(client, headers, "Saida", "SAIDA")
    first_camera = _camera(client, headers, int(first["id"]), "CAM-ENTRADA")
    second_camera = _camera(client, headers, int(second["id"]), "CAM-SAIDA")
    for plate, camera_id in (
        ("AAA1A11", first_camera["id"]),
        ("BBB2B22", second_camera["id"]),
    ):
        response = client.post(
            "/api/v1/plates/read-manual",
            json={"plate": plate, "camera_id": camera_id},
            headers=headers,
        )
        assert response.status_code == 201

    by_point = client.get(
        f"/api/v1/access-events?access_point_id={first['id']}", headers=headers
    )
    assert by_point.status_code == 200
    assert [item["plate_normalized"] for item in by_point.json()] == ["AAA1A11"]
    assert by_point.json()[0]["access_point"]["id"] == first["id"]

    by_camera = client.get(
        f"/api/v1/access-events?camera_id={second_camera['id']}", headers=headers
    )
    assert by_camera.status_code == 200
    assert [item["plate_normalized"] for item in by_camera.json()] == ["BBB2B22"]
    assert by_camera.json()[0]["plate_read"]["camera_id"] == second_camera["id"]

    summary = client.get(
        f"/api/v1/access-events/summary?camera_id={first_camera['id']}",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["total"] == 1

    recent = client.get(
        f"/api/v1/access-events/recent?access_point_id={second['id']}",
        headers=headers,
    )
    assert recent.status_code == 200
    assert len(recent.json()) == 1


def test_access_point_direction_best_effort_resolves_action_domain(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    action = client.post(
        "/api/v1/domains",
        json={
            "type": "ACAO_ACESSO",
            "code": "SAIDA",
            "name": "Saida",
        },
        headers=headers,
    )
    assert action.status_code == 201
    exit_point = _point(client, headers, "Portao Saida", "SAIDA")
    mixed_point = _point(client, headers, "Guarita Mista", "MISTO")

    exit_read = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "SAI1D23", "access_point_id": exit_point["id"]},
        headers=headers,
    )
    assert exit_read.status_code == 201
    assert exit_read.json()["action"] == "SAIDA"

    mixed_read = client.post(
        "/api/v1/plates/read-manual",
        json={"plate": "MIS2T34", "access_point_id": mixed_point["id"]},
        headers=headers,
    )
    assert mixed_read.status_code == 201
    assert mixed_read.json()["action"] is None


def test_image_read_accepts_logical_camera_metadata_without_physical_camera(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_dir = tmp_path / "plate_reads"
    monkeypatch.setattr(plate_service, "PLATE_READ_UPLOAD_DIR", upload_dir)
    headers = _admin_headers(client)
    point = _point(client, headers, "Portao Imagem", "ENTRADA")
    camera = _camera(client, headers, int(point["id"]), "CAM-IMAGEM")

    response = client.post(
        "/api/v1/plates/read-image",
        data={
            "mock_plate": "IMG1A23",
            "camera_id": str(camera["id"]),
            "vehicle_side": "TRASEIRA",
        },
        files={"file": ("imagem.jpg", b"fixture-local", "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["camera"]["id"] == camera["id"]
    assert body["access_point"]["id"] == point["id"]
    assert body["vehicle_side"] == "TRASEIRA"
    assert Path(body["image_path"]).read_bytes() == b"fixture-local"


def test_phase_6_9_migration_is_idempotent_on_legacy_sqlite_schema() -> None:
    engine = create_engine("sqlite+pysqlite://")
    metadata = MetaData()
    Table(
        "tblleiturasplacas",
        metadata,
        Column("intleituraplacaid", Integer, primary_key=True),
    )
    Table(
        "tbleventosacesso",
        metadata,
        Column("inteventoacessoid", Integer, primary_key=True),
    )
    metadata.create_all(engine)

    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "0017_access_points_cameras.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_0017_access_points_cameras", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        migration.upgrade()

        inspector = inspect(connection)
        assert {"tblpontosacesso", "tblcameras"}.issubset(
            inspector.get_table_names()
        )
        assert {"intcameraid", "strladoveiculo"}.issubset(
            column["name"]
            for column in inspector.get_columns("tblleiturasplacas")
        )
        assert "intpontoacessoid" in {
            column["name"]
            for column in inspector.get_columns("tbleventosacesso")
        }
        assert any(
            foreign_key["referred_table"] == "tblcameras"
            for foreign_key in inspector.get_foreign_keys("tblleiturasplacas")
        )
        assert any(
            foreign_key["referred_table"] == "tblpontosacesso"
            for foreign_key in inspector.get_foreign_keys("tbleventosacesso")
        )

    engine.dispose()
