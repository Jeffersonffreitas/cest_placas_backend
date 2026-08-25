"""Use the int prefix for identifiers and integer columns.

Revision ID: 0012_integer_column_prefixes
Revises: 0011_create_person_vehicle
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0012_integer_column_prefixes"
down_revision: str | None = "0011_create_person_vehicle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RENAMES = {
    "tblalunos": {"numalunoid": "intalunoid"},
    "tblpessoas": {"numpessoaid": "intpessoaid", "numcursoid": "intcursoid"},
    "tblveiculos": {
        "numveiculoid": "intveiculoid", "numalunoid": "intalunoid",
        "nummarcaid": "intmarcaid", "nummodeloid": "intmodeloid",
        "numcorid": "intcorid",
    },
    "tblpessoaveiculo": {
        "numpessoaveiculoid": "intpessoaveiculoid",
        "numpessoaid": "intpessoaid", "numveiculoid": "intveiculoid",
    },
    "tbldominios": {
        "numdominioid": "intdominioid", "numdominiopaiid": "intdominiopaiid",
    },
    "tblleiturasplacas": {
        "numleituraplacaid": "intleituraplacaid",
        "numveiculoid": "intveiculoid", "decconfianca": "numconfianca",
    },
    "tbleventosacesso": {
        "numeventoacessoid": "inteventoacessoid",
        "numveiculoid": "intveiculoid", "numalunoid": "intalunoid",
        "numleituraplacaid": "intleituraplacaid", "numacaoid": "intacaoid",
        "numorigemid": "intorigemid",
    },
    "tblusuarios": {"numusuarioid": "intusuarioid"},
    "tbllogsauditoria": {
        "numlogauditoriaid": "intlogauditoriaid",
        "numusuarioid": "intusuarioid", "numentidadeid": "intentidadeid",
    },
}

INDEX_RENAMES = {
    "tblpessoas": {"idx_tblpessoas_numcursoid": "idx_tblpessoas_intcursoid"},
    "tblveiculos": {
        "idx_tblveiculos_nummarcaid": "idx_tblveiculos_intmarcaid",
        "idx_tblveiculos_nummodeloid": "idx_tblveiculos_intmodeloid",
        "idx_tblveiculos_numcorid": "idx_tblveiculos_intcorid",
    },
    "tblpessoaveiculo": {
        "idx_tblpessoaveiculo_numpessoaid": "idx_tblpessoaveiculo_intpessoaid",
        "idx_tblpessoaveiculo_numveiculoid": "idx_tblpessoaveiculo_intveiculoid",
    },
}

# Explicit definitions also let a partially executed migration restore missing FKs.
FOREIGN_KEYS = (
    ("fk_tblveiculos_aluno", "tblveiculos", "intalunoid", "tblalunos", "intalunoid", "RESTRICT"),
    ("fk_tblveiculos_marca", "tblveiculos", "intmarcaid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tblveiculos_modelo", "tblveiculos", "intmodeloid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tblveiculos_cor", "tblveiculos", "intcorid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tblpessoas_curso", "tblpessoas", "intcursoid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tblpessoaveiculo_pessoa", "tblpessoaveiculo", "intpessoaid", "tblpessoas", "intpessoaid", "RESTRICT"),
    ("fk_tblpessoaveiculo_veiculo", "tblpessoaveiculo", "intveiculoid", "tblveiculos", "intveiculoid", "RESTRICT"),
    ("fk_tbldominios_pai", "tbldominios", "intdominiopaiid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tblleiturasplacas_veiculo", "tblleiturasplacas", "intveiculoid", "tblveiculos", "intveiculoid", "SET NULL"),
    ("fk_tbleventosacesso_aluno", "tbleventosacesso", "intalunoid", "tblalunos", "intalunoid", "SET NULL"),
    ("fk_tbleventosacesso_veiculo", "tbleventosacesso", "intveiculoid", "tblveiculos", "intveiculoid", "SET NULL"),
    ("fk_tbleventosacesso_leituraplaca", "tbleventosacesso", "intleituraplacaid", "tblleiturasplacas", "intleituraplacaid", "SET NULL"),
    ("fk_tbleventosacesso_acao", "tbleventosacesso", "intacaoid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tbleventosacesso_origem", "tbleventosacesso", "intorigemid", "tbldominios", "intdominioid", "RESTRICT"),
    ("fk_tbllogsauditoria_usuario", "tbllogsauditoria", "intusuarioid", "tblusuarios", "intusuarioid", "SET NULL"),
)


def _inspector():
    return inspect(op.get_bind())


def _tables() -> set[str]:
    return set(_inspector().get_table_names())


def _columns(table: str) -> dict[str, dict]:
    if table not in _tables():
        return {}
    return {column["name"]: column for column in _inspector().get_columns(table)}


def _foreign_keys(table: str) -> list[dict]:
    if table not in _tables():
        return []
    return _inspector().get_foreign_keys(table)


def _drop_affected_foreign_keys(rename_map: dict[str, dict[str, str]]) -> None:
    renamed = {(table, old) for table, names in rename_map.items() for old in names}
    renamed.update((table, new) for table, names in rename_map.items() for new in names.values())
    for table in _tables():
        for fk in _foreign_keys(table):
            name = fk.get("name")
            local = {(table, column) for column in fk.get("constrained_columns", [])}
            remote = {
                (fk.get("referred_table"), column)
                for column in fk.get("referred_columns", [])
            }
            if name and (local | remote) & renamed:
                op.drop_constraint(name, table, type_="foreignkey")


def _rename_columns(rename_map: dict[str, dict[str, str]]) -> None:
    for table, names in rename_map.items():
        columns = _columns(table)
        for old, new in names.items():
            if old not in columns or new in columns:
                continue
            column = columns[old]
            op.alter_column(
                table, old, new_column_name=new,
                existing_type=column["type"],
                existing_nullable=column.get("nullable", True),
                existing_server_default=column.get("default"),
                existing_autoincrement=column.get("autoincrement"),
            )
            columns = _columns(table)


def _rename_indexes(index_map: dict[str, dict[str, str]]) -> None:
    for table, names in index_map.items():
        if table not in _tables():
            continue
        indexes = {index["name"] for index in _inspector().get_indexes(table)}
        for old, new in names.items():
            if old in indexes and new not in indexes:
                op.execute(sa.text(f"ALTER TABLE `{table}` RENAME INDEX `{old}` TO `{new}`"))
                indexes.remove(old)
                indexes.add(new)


def _restore_foreign_keys(rename_map: dict[str, dict[str, str]]) -> None:
    for name, table, column, target, target_column, ondelete in FOREIGN_KEYS:
        column = rename_map.get(table, {}).get(column, column)
        target_column = rename_map.get(target, {}).get(target_column, target_column)
        if column not in _columns(table) or target_column not in _columns(target):
            continue
        existing = _foreign_keys(table)
        if any(
            fk.get("name") == name
            or (
                fk.get("constrained_columns") == [column]
                and fk.get("referred_table") == target
                and fk.get("referred_columns") == [target_column]
            )
            for fk in existing
        ):
            continue
        op.create_foreign_key(
            name, table, target, [column], [target_column], ondelete=ondelete
        )


def _run(rename_map: dict[str, dict[str, str]], index_map: dict[str, dict[str, str]]) -> None:
    if op.get_bind().dialect.name not in {"mysql", "mariadb"}:
        raise RuntimeError("Esta migration deve ser executada em MySQL ou MariaDB")
    _drop_affected_foreign_keys(rename_map)
    _rename_columns(rename_map)
    _rename_indexes(index_map)
    _restore_foreign_keys(rename_map)


def upgrade() -> None:
    _run(RENAMES, INDEX_RENAMES)


def downgrade() -> None:
    reverse_columns = {
        table: {new: old for old, new in names.items()}
        for table, names in RENAMES.items()
    }
    reverse_indexes = {
        table: {new: old for old, new in names.items()}
        for table, names in INDEX_RENAMES.items()
    }
    _run(reverse_columns, reverse_indexes)
