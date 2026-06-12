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
            "IntAlunoid",
            "StrMatricula",
            "StrNomeCompleto",
            "StrEmail",
            "StrTelefone",
            "IntAtivo",
            "DtdCriacao",
            "DtdAtualizacao",
        },
        "tblveiculos": {
            "IntVeiculoid",
            "IntAlunoid",
            "StrPlaca",
            "StrMarca",
            "StrModelo",
            "StrCor",
            "IntAtivo",
            "DtdCriacao",
            "DtdAtualizacao",
        },
        "tblleiturasplacas": {
            "IntLeituraPlacaid",
            "IntVeiculoid",
            "StrPlaca",
            "StrOrigem",
            "DecConfianca",
            "StrCaminhoImagem",
            "DtdLeitura",
            "DtdCriacao",
            "DtdAtualizacao",
        },
        "tbleventosacesso": {
            "IntEventoAcessoid",
            "IntVeiculoid",
            "IntAlunoid",
            "StrSituacao",
            "DtdCriacao",
            "StrPlacaEntrada",
            "StrPlacaNormalizada",
            "StrOrigem",
        },
        "tblusuarios": {
            "IntUsuarioid",
            "StrUsuario",
            "StrNomeCompleto",
            "StrSenhaHash",
            "IntAtivo",
            "IntSuperUsuario",
            "DtdCriacao",
            "DtdAtualizacao",
        },
        "tbllogsauditoria": {
            "IntLogAuditoriaid",
            "IntUsuarioid",
            "StrAcao",
            "StrEntidade",
            "IntEntidadeid",
            "StrDetalhes",
            "DtdCriacao",
        },
    }

    for table_name, expected_columns in expected_columns_by_table.items():
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert expected_columns.issubset(actual_columns)

    assert models.Student.id.property.columns[0].name == "IntAlunoid"
    assert models.Student.id.key == "id"
    assert models.Vehicle.student_id.property.columns[0].name == "IntAlunoid"
    assert models.AccessEvent.plate_normalized.property.columns[0].name == "StrPlacaNormalizada"
    assert models.User.username.property.columns[0].name == "StrUsuario"
