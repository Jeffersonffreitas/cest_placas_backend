"""rename tables and columns to portuguese standard

Revision ID: 0006_rename_tables_columns_to_portuguese
Revises: 0005_rename_domain_columns_faculty_standard
Create Date: 2026-06-12 16:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0006_rename_tables_columns_to_portuguese"
down_revision: Union[str, None] = "0005_rename_domain_columns_faculty_standard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> object:
    return inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _table_columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _foreign_key_exists(table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        foreign_key["name"] == constraint_name
        for foreign_key in _inspector().get_foreign_keys(table_name)
    )


def _foreign_key_for_columns_exists(
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> bool:
    if not _table_exists(source_table):
        return False
    return any(
        foreign_key["referred_table"] == referent_table
        and foreign_key["constrained_columns"] == local_cols
        and foreign_key["referred_columns"] == remote_cols
        for foreign_key in _inspector().get_foreign_keys(source_table)
    )


def _rename_table(old_name: str, new_name: str) -> None:
    if _table_exists(old_name) and not _table_exists(new_name):
        op.rename_table(old_name, new_name)


def _rename_column(
    table_name: str,
    old_name: str,
    new_name: str,
    existing_type: object,
    *,
    existing_nullable: bool,
    existing_server_default: str | sa.TextClause | None = None,
    existing_autoincrement: bool | None = None,
) -> None:
    columns = _table_columns(table_name)
    if old_name not in columns or new_name in columns:
        return
    op.alter_column(
        table_name,
        old_name,
        new_column_name=new_name,
        existing_type=existing_type,
        existing_nullable=existing_nullable,
        existing_server_default=existing_server_default,
        existing_autoincrement=existing_autoincrement,
    )


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _create_index_if_missing(
    table_name: str,
    index_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if _index_exists(table_name, index_name):
        return
    if set(columns).issubset(_table_columns(table_name)):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_foreign_key_if_exists(table_name: str, constraint_name: str) -> None:
    if _foreign_key_exists(table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def _create_foreign_key_if_missing(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    *,
    ondelete: str,
) -> None:
    if _foreign_key_exists(source_table, constraint_name):
        return
    if _foreign_key_for_columns_exists(source_table, referent_table, local_cols, remote_cols):
        return
    if not set(local_cols).issubset(_table_columns(source_table)):
        return
    if not set(remote_cols).issubset(_table_columns(referent_table)):
        return
    op.create_foreign_key(
        constraint_name,
        source_table,
        referent_table,
        local_cols,
        remote_cols,
        ondelete=ondelete,
    )


def _drop_old_foreign_keys() -> None:
    for table_name in ("vehicles", "tblveiculos"):
        _drop_foreign_key_if_exists(table_name, "fk_vehicles_student_id_students")
        _drop_foreign_key_if_exists(table_name, "fk_tblveiculos_aluno")
    for table_name in ("plate_reads", "tblleiturasplacas"):
        _drop_foreign_key_if_exists(table_name, "fk_plate_reads_vehicle_id_vehicles")
        _drop_foreign_key_if_exists(table_name, "fk_tblleiturasplacas_veiculo")
    for table_name in ("access_events", "tbleventosacesso"):
        _drop_foreign_key_if_exists(table_name, "fk_access_events_student_id_students")
        _drop_foreign_key_if_exists(table_name, "fk_access_events_vehicle_id_vehicles")
        _drop_foreign_key_if_exists(table_name, "fk_tbleventosacesso_aluno")
        _drop_foreign_key_if_exists(table_name, "fk_tbleventosacesso_veiculo")
    for table_name in ("audit_logs", "tbllogsauditoria"):
        _drop_foreign_key_if_exists(table_name, "fk_audit_logs_user_id_users")
        _drop_foreign_key_if_exists(table_name, "fk_tbllogsauditoria_usuario")


def _rename_tables_to_portuguese() -> None:
    _rename_table("students", "tblalunos")
    _rename_table("vehicles", "tblveiculos")
    _rename_table("plate_reads", "tblleiturasplacas")
    _rename_table("access_events", "tbleventosacesso")
    _rename_table("users", "tblusuarios")
    _rename_table("audit_logs", "tbllogsauditoria")


def _rename_tables_to_english() -> None:
    _rename_table("tblalunos", "students")
    _rename_table("tblveiculos", "vehicles")
    _rename_table("tblleiturasplacas", "plate_reads")
    _rename_table("tbleventosacesso", "access_events")
    _rename_table("tblusuarios", "users")
    _rename_table("tbllogsauditoria", "audit_logs")


def _rename_columns_to_portuguese() -> None:
    _rename_column("tblalunos", "IntStudentid", "IntAlunoid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("tblalunos", "StrRegistrationNumber", "StrMatricula", sa.String(length=50), existing_nullable=False)
    _rename_column("tblalunos", "StrFullName", "StrNomeCompleto", sa.String(length=255), existing_nullable=False)
    _rename_column("tblalunos", "StrPhone", "StrTelefone", sa.String(length=20), existing_nullable=True)
    _rename_column("tblalunos", "IntIsActive", "IntAtivo", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column("tblalunos", "DtdCreatedAt", "DtdCriacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("tblalunos", "DtdUpdatedAt", "DtdAtualizacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("tblveiculos", "IntVehicleid", "IntVeiculoid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("tblveiculos", "IntStudentid", "IntAlunoid", sa.Integer(), existing_nullable=False)
    _rename_column("tblveiculos", "StrPlate", "StrPlaca", sa.String(length=10), existing_nullable=False)
    _rename_column("tblveiculos", "StrBrand", "StrMarca", sa.String(length=100), existing_nullable=True)
    _rename_column("tblveiculos", "StrModel", "StrModelo", sa.String(length=100), existing_nullable=True)
    _rename_column("tblveiculos", "StrColor", "StrCor", sa.String(length=50), existing_nullable=True)
    _rename_column("tblveiculos", "IntIsActive", "IntAtivo", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column("tblveiculos", "DtdCreatedAt", "DtdCriacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("tblveiculos", "DtdUpdatedAt", "DtdAtualizacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("tblleiturasplacas", "IntPlateReadid", "IntLeituraPlacaid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("tblleiturasplacas", "IntVehicleid", "IntVeiculoid", sa.Integer(), existing_nullable=True)
    _rename_column("tblleiturasplacas", "StrPlate", "StrPlaca", sa.String(length=10), existing_nullable=False)
    _rename_column("tblleiturasplacas", "StrSource", "StrOrigem", sa.String(length=30), existing_nullable=False, existing_server_default="manual")
    _rename_column("tblleiturasplacas", "DecConfidence", "DecConfianca", sa.Numeric(precision=5, scale=2), existing_nullable=True)
    _rename_column("tblleiturasplacas", "StrImagePath", "StrCaminhoImagem", sa.String(length=255), existing_nullable=True)
    _rename_column("tblleiturasplacas", "DtdReadAt", "DtdLeitura", sa.DateTime(), existing_nullable=False)
    _rename_column("tblleiturasplacas", "DtdCreatedAt", "DtdCriacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("tblleiturasplacas", "DtdUpdatedAt", "DtdAtualizacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("tbleventosacesso", "IntAccessEventid", "IntEventoAcessoid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("tbleventosacesso", "IntVehicleid", "IntVeiculoid", sa.Integer(), existing_nullable=True)
    _rename_column("tbleventosacesso", "IntStudentid", "IntAlunoid", sa.Integer(), existing_nullable=True)
    _rename_column("tbleventosacesso", "StrStatus", "StrSituacao", sa.String(length=20), existing_nullable=False)
    _rename_column("tbleventosacesso", "DtdCreatedAt", "DtdCriacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("tbleventosacesso", "StrPlateInput", "StrPlacaEntrada", sa.String(length=20), existing_nullable=False)
    _rename_column("tbleventosacesso", "StrPlateNormalized", "StrPlacaNormalizada", sa.String(length=10), existing_nullable=False)
    _rename_column("tbleventosacesso", "StrSource", "StrOrigem", sa.String(length=30), existing_nullable=False, existing_server_default="manual")

    _rename_column("tblusuarios", "id", "IntUsuarioid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("tblusuarios", "username", "StrUsuario", sa.String(length=100), existing_nullable=False)
    _rename_column("tblusuarios", "full_name", "StrNomeCompleto", sa.String(length=255), existing_nullable=True)
    _rename_column("tblusuarios", "password_hash", "StrSenhaHash", sa.String(length=255), existing_nullable=False)
    _rename_column("tblusuarios", "is_active", "IntAtivo", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column("tblusuarios", "is_superuser", "IntSuperUsuario", sa.Boolean(), existing_nullable=False, existing_server_default="0")
    _rename_column("tblusuarios", "created_at", "DtdCriacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("tblusuarios", "updated_at", "DtdAtualizacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("tbllogsauditoria", "id", "IntLogAuditoriaid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("tbllogsauditoria", "user_id", "IntUsuarioid", sa.Integer(), existing_nullable=True)
    _rename_column("tbllogsauditoria", "action", "StrAcao", sa.String(length=100), existing_nullable=False)
    _rename_column("tbllogsauditoria", "entity_name", "StrEntidade", sa.String(length=100), existing_nullable=False)
    _rename_column("tbllogsauditoria", "entity_id", "IntEntidadeid", sa.String(length=50), existing_nullable=True)
    _rename_column("tbllogsauditoria", "details", "StrDetalhes", sa.JSON(), existing_nullable=True)
    _rename_column("tbllogsauditoria", "created_at", "DtdCriacao", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))


def _rename_columns_to_english() -> None:
    _rename_column("students", "IntAlunoid", "IntStudentid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("students", "StrMatricula", "StrRegistrationNumber", sa.String(length=50), existing_nullable=False)
    _rename_column("students", "StrNomeCompleto", "StrFullName", sa.String(length=255), existing_nullable=False)
    _rename_column("students", "StrTelefone", "StrPhone", sa.String(length=20), existing_nullable=True)
    _rename_column("students", "IntAtivo", "IntIsActive", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column("students", "DtdCriacao", "DtdCreatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("students", "DtdAtualizacao", "DtdUpdatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("vehicles", "IntVeiculoid", "IntVehicleid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("vehicles", "IntAlunoid", "IntStudentid", sa.Integer(), existing_nullable=False)
    _rename_column("vehicles", "StrPlaca", "StrPlate", sa.String(length=10), existing_nullable=False)
    _rename_column("vehicles", "StrMarca", "StrBrand", sa.String(length=100), existing_nullable=True)
    _rename_column("vehicles", "StrModelo", "StrModel", sa.String(length=100), existing_nullable=True)
    _rename_column("vehicles", "StrCor", "StrColor", sa.String(length=50), existing_nullable=True)
    _rename_column("vehicles", "IntAtivo", "IntIsActive", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column("vehicles", "DtdCriacao", "DtdCreatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("vehicles", "DtdAtualizacao", "DtdUpdatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("plate_reads", "IntLeituraPlacaid", "IntPlateReadid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("plate_reads", "IntVeiculoid", "IntVehicleid", sa.Integer(), existing_nullable=True)
    _rename_column("plate_reads", "StrPlaca", "StrPlate", sa.String(length=10), existing_nullable=False)
    _rename_column("plate_reads", "StrOrigem", "StrSource", sa.String(length=30), existing_nullable=False, existing_server_default="manual")
    _rename_column("plate_reads", "DecConfianca", "DecConfidence", sa.Numeric(precision=5, scale=2), existing_nullable=True)
    _rename_column("plate_reads", "StrCaminhoImagem", "StrImagePath", sa.String(length=255), existing_nullable=True)
    _rename_column("plate_reads", "DtdLeitura", "DtdReadAt", sa.DateTime(), existing_nullable=False)
    _rename_column("plate_reads", "DtdCriacao", "DtdCreatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("plate_reads", "DtdAtualizacao", "DtdUpdatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("access_events", "IntEventoAcessoid", "IntAccessEventid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("access_events", "IntVeiculoid", "IntVehicleid", sa.Integer(), existing_nullable=True)
    _rename_column("access_events", "IntAlunoid", "IntStudentid", sa.Integer(), existing_nullable=True)
    _rename_column("access_events", "StrSituacao", "StrStatus", sa.String(length=20), existing_nullable=False)
    _rename_column("access_events", "DtdCriacao", "DtdCreatedAt", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("access_events", "StrPlacaEntrada", "StrPlateInput", sa.String(length=20), existing_nullable=False)
    _rename_column("access_events", "StrPlacaNormalizada", "StrPlateNormalized", sa.String(length=10), existing_nullable=False)
    _rename_column("access_events", "StrOrigem", "StrSource", sa.String(length=30), existing_nullable=False, existing_server_default="manual")

    _rename_column("users", "IntUsuarioid", "id", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("users", "StrUsuario", "username", sa.String(length=100), existing_nullable=False)
    _rename_column("users", "StrNomeCompleto", "full_name", sa.String(length=255), existing_nullable=True)
    _rename_column("users", "StrSenhaHash", "password_hash", sa.String(length=255), existing_nullable=False)
    _rename_column("users", "IntAtivo", "is_active", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column("users", "IntSuperUsuario", "is_superuser", sa.Boolean(), existing_nullable=False, existing_server_default="0")
    _rename_column("users", "DtdCriacao", "created_at", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))
    _rename_column("users", "DtdAtualizacao", "updated_at", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))

    _rename_column("audit_logs", "IntLogAuditoriaid", "id", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("audit_logs", "IntUsuarioid", "user_id", sa.Integer(), existing_nullable=True)
    _rename_column("audit_logs", "StrAcao", "action", sa.String(length=100), existing_nullable=False)
    _rename_column("audit_logs", "StrEntidade", "entity_name", sa.String(length=100), existing_nullable=False)
    _rename_column("audit_logs", "IntEntidadeid", "entity_id", sa.String(length=50), existing_nullable=True)
    _rename_column("audit_logs", "StrDetalhes", "details", sa.JSON(), existing_nullable=True)
    _rename_column("audit_logs", "DtdCriacao", "created_at", sa.DateTime(), existing_nullable=False, existing_server_default=sa.text("CURRENT_TIMESTAMP"))


def _replace_indexes_with_portuguese_names() -> None:
    for table_name, old_name in (
        ("tblusuarios", "ix_users_username"),
        ("tblalunos", "ix_students_registration_number"),
        ("tblalunos", "ix_students_email"),
        ("tblveiculos", "ix_vehicles_plate"),
        ("tblveiculos", "ix_vehicles_student_id"),
        ("tblleiturasplacas", "ix_plate_reads_plate"),
        ("tblleiturasplacas", "ix_plate_reads_read_at"),
        ("tbleventosacesso", "ix_access_events_plate_normalized"),
        ("tbleventosacesso", "ix_access_events_source"),
        ("tbleventosacesso", "ix_access_events_status"),
        ("tbleventosacesso", "ix_access_events_student_id"),
        ("tbleventosacesso", "ix_access_events_vehicle_id"),
        ("tbleventosacesso", "ix_access_events_created_at"),
        ("tbllogsauditoria", "ix_audit_logs_created_at"),
        ("tbllogsauditoria", "ix_audit_logs_entity_name"),
    ):
        _drop_index_if_exists(table_name, old_name)

    _create_index_if_missing("tblusuarios", "ix_tblusuarios_usuario", ["StrUsuario"], unique=True)
    _create_index_if_missing("tblalunos", "ix_tblalunos_matricula", ["StrMatricula"], unique=True)
    _create_index_if_missing("tblalunos", "ix_tblalunos_email", ["StrEmail"], unique=True)
    _create_index_if_missing("tblveiculos", "ix_tblveiculos_placa", ["StrPlaca"], unique=True)
    _create_index_if_missing("tblveiculos", "ix_tblveiculos_aluno", ["IntAlunoid"])
    _create_index_if_missing("tblleiturasplacas", "ix_tblleiturasplacas_placa", ["StrPlaca"])
    _create_index_if_missing("tblleiturasplacas", "ix_tblleiturasplacas_leitura", ["DtdLeitura"])
    _create_index_if_missing("tbleventosacesso", "ix_tbleventosacesso_placa_normalizada", ["StrPlacaNormalizada"])
    _create_index_if_missing("tbleventosacesso", "ix_tbleventosacesso_origem", ["StrOrigem"])
    _create_index_if_missing("tbleventosacesso", "ix_tbleventosacesso_situacao", ["StrSituacao"])
    _create_index_if_missing("tbleventosacesso", "ix_tbleventosacesso_aluno", ["IntAlunoid"])
    _create_index_if_missing("tbleventosacesso", "ix_tbleventosacesso_veiculo", ["IntVeiculoid"])
    _create_index_if_missing("tbleventosacesso", "ix_tbleventosacesso_criacao", ["DtdCriacao"])
    _create_index_if_missing("tbllogsauditoria", "ix_tbllogsauditoria_criacao", ["DtdCriacao"])
    _create_index_if_missing("tbllogsauditoria", "ix_tbllogsauditoria_entidade", ["StrEntidade"])


def _replace_indexes_with_english_names() -> None:
    for table_name, old_name in (
        ("users", "ix_tblusuarios_usuario"),
        ("students", "ix_tblalunos_matricula"),
        ("students", "ix_tblalunos_email"),
        ("vehicles", "ix_tblveiculos_placa"),
        ("vehicles", "ix_tblveiculos_aluno"),
        ("plate_reads", "ix_tblleiturasplacas_placa"),
        ("plate_reads", "ix_tblleiturasplacas_leitura"),
        ("access_events", "ix_tbleventosacesso_placa_normalizada"),
        ("access_events", "ix_tbleventosacesso_origem"),
        ("access_events", "ix_tbleventosacesso_situacao"),
        ("access_events", "ix_tbleventosacesso_aluno"),
        ("access_events", "ix_tbleventosacesso_veiculo"),
        ("access_events", "ix_tbleventosacesso_criacao"),
        ("audit_logs", "ix_tbllogsauditoria_criacao"),
        ("audit_logs", "ix_tbllogsauditoria_entidade"),
    ):
        _drop_index_if_exists(table_name, old_name)

    _create_index_if_missing("users", "ix_users_username", ["username"], unique=True)
    _create_index_if_missing("students", "ix_students_registration_number", ["StrRegistrationNumber"], unique=True)
    _create_index_if_missing("students", "ix_students_email", ["StrEmail"], unique=True)
    _create_index_if_missing("vehicles", "ix_vehicles_plate", ["StrPlate"], unique=True)
    _create_index_if_missing("vehicles", "ix_vehicles_student_id", ["IntStudentid"])
    _create_index_if_missing("plate_reads", "ix_plate_reads_plate", ["StrPlate"])
    _create_index_if_missing("plate_reads", "ix_plate_reads_read_at", ["DtdReadAt"])
    _create_index_if_missing("access_events", "ix_access_events_plate_normalized", ["StrPlateNormalized"])
    _create_index_if_missing("access_events", "ix_access_events_source", ["StrSource"])
    _create_index_if_missing("access_events", "ix_access_events_status", ["StrStatus"])
    _create_index_if_missing("access_events", "ix_access_events_student_id", ["IntStudentid"])
    _create_index_if_missing("access_events", "ix_access_events_vehicle_id", ["IntVehicleid"])
    _create_index_if_missing("access_events", "ix_access_events_created_at", ["DtdCreatedAt"])
    _create_index_if_missing("audit_logs", "ix_audit_logs_created_at", ["created_at"])
    _create_index_if_missing("audit_logs", "ix_audit_logs_entity_name", ["entity_name"])


def _create_portuguese_foreign_keys() -> None:
    _create_foreign_key_if_missing(
        "fk_tblveiculos_aluno",
        "tblveiculos",
        "tblalunos",
        ["IntAlunoid"],
        ["IntAlunoid"],
        ondelete="RESTRICT",
    )
    _create_foreign_key_if_missing(
        "fk_tblleiturasplacas_veiculo",
        "tblleiturasplacas",
        "tblveiculos",
        ["IntVeiculoid"],
        ["IntVeiculoid"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_tbleventosacesso_aluno",
        "tbleventosacesso",
        "tblalunos",
        ["IntAlunoid"],
        ["IntAlunoid"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_tbleventosacesso_veiculo",
        "tbleventosacesso",
        "tblveiculos",
        ["IntVeiculoid"],
        ["IntVeiculoid"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_tbllogsauditoria_usuario",
        "tbllogsauditoria",
        "tblusuarios",
        ["IntUsuarioid"],
        ["IntUsuarioid"],
        ondelete="SET NULL",
    )


def _create_english_foreign_keys() -> None:
    _create_foreign_key_if_missing(
        "fk_vehicles_student_id_students",
        "vehicles",
        "students",
        ["IntStudentid"],
        ["IntStudentid"],
        ondelete="RESTRICT",
    )
    _create_foreign_key_if_missing(
        "fk_plate_reads_vehicle_id_vehicles",
        "plate_reads",
        "vehicles",
        ["IntVehicleid"],
        ["IntVehicleid"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_access_events_student_id_students",
        "access_events",
        "students",
        ["IntStudentid"],
        ["IntStudentid"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_access_events_vehicle_id_vehicles",
        "access_events",
        "vehicles",
        ["IntVehicleid"],
        ["IntVehicleid"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_audit_logs_user_id_users",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def upgrade() -> None:
    _drop_old_foreign_keys()
    _rename_tables_to_portuguese()
    _rename_columns_to_portuguese()
    _replace_indexes_with_portuguese_names()
    _create_portuguese_foreign_keys()


def downgrade() -> None:
    _drop_old_foreign_keys()
    _rename_tables_to_english()
    _rename_columns_to_english()
    _replace_indexes_with_english_names()
    _create_english_foreign_keys()
