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
            "intalunoid",
            "strmatricula",
            "strnomecompleto",
            "stremail",
            "strtelefone",
            "bolativo",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tblveiculos": {
            "intveiculoid",
            "strplaca",
            "strmarca",
            "strmodelo",
            "strcor",
            "intmarcaid",
            "intmodeloid",
            "intcorid",
            "bolativo",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tblpessoas": {
            "intpessoaid",
            "intcursoid",
            "strtipopessoa",
            "strmatricula",
            "strnomecompleto",
            "bolativo",
        },
        "tbldominios": {
            "intdominioid",
            "intdominiopaiid",
            "strtipo",
            "strcodigo",
            "strnome",
            "bolativo",
        },
        "tblpessoaveiculo": {
            "intpessoaveiculoid",
            "intpessoaid",
            "intveiculoid",
            "bolativo",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tblleiturasplacas": {
            "intleituraplacaid",
            "intveiculoid",
            "strplaca",
            "strorigem",
            "numconfianca",
            "strcaminhoimagem",
            "dtaleitura",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tbleventosacesso": {
            "inteventoacessoid",
            "intveiculoid",
            "intalunoid",
            "strsituacao",
            "dtacriacao",
            "strplacaentrada",
            "strplacanormalizada",
            "strorigem",
        },
        "tblusuarios": {
            "intusuarioid",
            "strusuario",
            "strnomecompleto",
            "strsenhahash",
            "bolativo",
            "bolsuperusuario",
            "dtacriacao",
            "dtaatualizacao",
        },
        "tbllogsauditoria": {
            "intlogauditoriaid",
            "intusuarioid",
            "stracao",
            "strentidade",
            "intentidadeid",
            "strdetalhes",
            "dtacriacao",
        },
    }

    for table_name, expected_columns in expected_columns_by_table.items():
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert expected_columns.issubset(actual_columns)

    assert models.Student.id.property.columns[0].name == "intalunoid"
    assert models.Student.id.key == "id"
    assert "intalunoid" not in {
        column.name for column in models.Vehicle.__table__.columns
    }
    assert models.PersonVehicle.person_id.property.columns[0].name == "intpessoaid"
    assert models.PersonVehicle.vehicle_id.property.columns[0].name == "intveiculoid"
    assert models.AccessEvent.plate_normalized.property.columns[0].name == "strplacanormalizada"
    assert models.User.username.property.columns[0].name == "strusuario"


def test_main_models_still_persist_with_python_attribute_names(
    db_session: Session,
) -> None:
    person = models.Person(
        person_type="ALUNO",
        registration_number="MIG-001",
        full_name="Teste Migration",
    )
    db_session.add(person)
    db_session.flush()

    vehicle = models.Vehicle(plate="MIG1A23")
    db_session.add(vehicle)
    db_session.flush()
    db_session.add(models.PersonVehicle(person_id=person.id, vehicle_id=vehicle.id))
    db_session.commit()

    persisted = db_session.get(models.Vehicle, vehicle.id)
    assert persisted is not None
    assert persisted.student_id == person.id
    assert persisted.plate == "MIG1A23"
