from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm import Session

from app import models


def test_all_models_can_be_imported_and_mappers_configured() -> None:
    assert models.Student.__tablename__ == "students"
    assert models.AccessEvent.__tablename__ == "access_events"

    configure_mappers()


def test_domain_models_use_faculty_database_column_names(db_session: Session) -> None:
    inspector = inspect(db_session.bind)

    expected_columns_by_table = {
        "students": {
            "IntStudentid",
            "StrRegistrationNumber",
            "StrFullName",
            "StrEmail",
            "StrPhone",
            "IntIsActive",
            "DtdCreatedAt",
            "DtdUpdatedAt",
        },
        "vehicles": {
            "IntVehicleid",
            "IntStudentid",
            "StrPlate",
            "StrBrand",
            "StrModel",
            "StrColor",
            "IntIsActive",
            "DtdCreatedAt",
            "DtdUpdatedAt",
        },
        "plate_reads": {
            "IntPlateReadid",
            "IntVehicleid",
            "StrPlate",
            "StrSource",
            "DecConfidence",
            "StrImagePath",
            "DtdReadAt",
            "DtdCreatedAt",
            "DtdUpdatedAt",
        },
        "access_events": {
            "IntAccessEventid",
            "IntVehicleid",
            "IntStudentid",
            "StrStatus",
            "DtdCreatedAt",
            "StrPlateInput",
            "StrPlateNormalized",
            "StrSource",
        },
    }

    for table_name, expected_columns in expected_columns_by_table.items():
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert expected_columns.issubset(actual_columns)

    assert models.Student.id.property.columns[0].name == "IntStudentid"
    assert models.Student.id.key == "id"
    assert models.Vehicle.student_id.property.columns[0].name == "IntStudentid"
    assert models.AccessEvent.plate_normalized.property.columns[0].name == "StrPlateNormalized"
