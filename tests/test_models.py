from sqlalchemy.orm import configure_mappers

from app import models


def test_all_models_can_be_imported_and_mappers_configured() -> None:
    assert models.Student.__tablename__ == "students"
    assert models.AccessEvent.__tablename__ == "access_events"

    configure_mappers()
