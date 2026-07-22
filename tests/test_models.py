from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm import Session

from app import models


def test_all_models_can_be_imported_and_mappers_configured() -> None:
    assert models.Student.__tablename__ == "tblalunos"
    assert models.AccessEvent.__tablename__ == "tbleventosacesso"

    configure_mappers()


def test_models_use_portuguese_database_table_and_column_names(db_session: Session) -> None:
    inspector = inspect(db_session.bind)

    expected_columns_by_table = {
        "tblalunos": {
            "numalunoid",
            "strmatricula",
            "strnomecompleto",
            "stremail",
            "strtelefone",
            "bolativo",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tblveiculos": {
            "numveiculoid",
            "numalunoid",
            "strplaca",
            "strmarca",
            "strmodelo",
            "strcor",
            "bolativo",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tblleiturasplacas": {
            "numleituraplacaid",
            "numveiculoid",
            "strplaca",
            "strorigem",
            "decconfianca",
            "strcaminhoimagem",
            "dtaleitura",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tbleventosacesso": {
            "numeventoacessoid",
            "numveiculoid",
            "numalunoid",
            "strsituacao",
            "dtacriacao",
            "strplacaentrada",
            "strplacanormalizada",
            "strorigem",
        },
        "tblusuarios": {
            "numusuarioid",
            "strusuario",
            "strnomecompleto",
            "strsenhahash",
            "bolativo",
            "bolsuperusuario",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tbllogsauditoria": {
            "numlogauditoriaid",
            "numusuarioid",
            "stracao",
            "strentidade",
            "numentidadeid",
            "strdetalhes",
            "dtacriacao",
        },
    }

    for table_name, expected_columns in expected_columns_by_table.items():
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert expected_columns.issubset(actual_columns)

    assert models.Student.id.property.columns[0].name == "numalunoid"
    assert models.Student.id.key == "id"
    assert models.Vehicle.student_id.property.columns[0].name == "numalunoid"
    assert models.AccessEvent.plate_normalized.property.columns[0].name == "strplacanormalizada"
    assert models.User.username.property.columns[0].name == "strusuario"
