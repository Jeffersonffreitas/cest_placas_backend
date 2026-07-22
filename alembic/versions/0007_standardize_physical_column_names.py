"""Standardize physical column names without recreating tables or data."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0007_column_names_lowercase"
down_revision: str | None = "0006_rename_tables_columns_to_portuguese"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Each target accepts both legacy Int and intermediate Num names where applicable.
RENAMES = {
    "tblalunos": {
        "numalunoid": ("IntAlunoid", "NumAlunoid"), "strmatricula": ("StrMatricula",),
        "strnomecompleto": ("StrNomeCompleto",), "stremail": ("StrEmail",),
        "strtelefone": ("StrTelefone",), "bolativo": ("IntAtivo", "NumAtivo"),
        "dtacriacao": ("DtdCriacao",), "dtaatualizacao": ("DtdAtualizacao",),
    },
    "tblveiculos": {
        "numveiculoid": ("IntVeiculoid", "NumVeiculoid"),
        "numalunoid": ("IntAlunoid", "NumAlunoid"), "strplaca": ("StrPlaca",),
        "strmarca": ("StrMarca",), "strmodelo": ("StrModelo",), "strcor": ("StrCor",),
        "bolativo": ("IntAtivo", "NumAtivo"), "dtacriacao": ("DtdCriacao",),
        "dtaatualizacao": ("DtdAtualizacao",),
    },
    "tblleiturasplacas": {
        "numleituraplacaid": ("IntLeituraPlacaid", "NumLeituraPlacaid"),
        "numveiculoid": ("IntVeiculoid", "NumVeiculoid"), "strplaca": ("StrPlaca",),
        "strorigem": ("StrOrigem",), "decconfianca": ("DecConfianca",),
        "strcaminhoimagem": ("StrCaminhoImagem",), "dtaleitura": ("DtdLeitura",),
        "dtacriacao": ("DtdCriacao",), "dtaatualizacao": ("DtdAtualizacao",),
    },
    "tbleventosacesso": {
        "numeventoacessoid": ("IntEventoAcessoid", "NumEventoAcessoid"),
        "numveiculoid": ("IntVeiculoid", "NumVeiculoid"),
        "numalunoid": ("IntAlunoid", "NumAlunoid"), "strsituacao": ("StrSituacao",),
        "dtacriacao": ("DtdCriacao",), "strplacaentrada": ("StrPlacaEntrada",),
        "strplacanormalizada": ("StrPlacaNormalizada",), "strorigem": ("StrOrigem",),
    },
    "tblusuarios": {
        "numusuarioid": ("IntUsuarioid", "NumUsuarioid"), "strusuario": ("StrUsuario",),
        "strnomecompleto": ("StrNomeCompleto",), "strsenhahash": ("StrSenhaHash",),
        "bolativo": ("IntAtivo", "NumAtivo"),
        "bolsuperusuario": ("IntSuperUsuario", "NumSuperUsuario"),
        "dtacriacao": ("DtdCriacao",), "dtaatualizacao": ("DtdAtualizacao",),
    },
    "tbllogsauditoria": {
        "numlogauditoriaid": ("IntLogAuditoriaid", "NumLogAuditoriaid"),
        "numusuarioid": ("IntUsuarioid", "NumUsuarioid"), "stracao": ("StrAcao",),
        "strentidade": ("StrEntidade",),
        "numentidadeid": ("IntEntidadeid", "NumEntidadeid"),
        "strdetalhes": ("StrDetalhes",), "dtacriacao": ("DtdCriacao",),
    },
}


def _columns(table_name: str) -> dict[str, dict]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def _datetime_default(column_name: str) -> sa.TextClause | None:
    """Return MySQL expressions, never quoted strings, for datetime defaults."""
    if column_name in {"dtacriacao", "DtdCriacao"}:
        return sa.text("CURRENT_TIMESTAMP")
    if column_name in {"dtaatualizacao", "DtdAtualizacao"}:
        return sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    return None


def _rename(table_name: str, old_names: tuple[str, ...], new_name: str) -> None:
    columns = _columns(table_name)
    if not columns:
        return
    if new_name in columns:
        return
    old_name = next((name for name in old_names if name in columns), None)
    if old_name is None:
        return
    column = columns[old_name]
    datetime_default = _datetime_default(new_name)
    existing_server_default = datetime_default
    if existing_server_default is None:
        existing_server_default = column.get("default")
    if existing_server_default is None:
        existing_server_default = column.get("server_default")
    op.alter_column(
        table_name, old_name, new_column_name=new_name,
        existing_type=column["type"], existing_nullable=column.get("nullable", True),
        existing_server_default=existing_server_default,
        server_default=datetime_default if datetime_default is not None else False,
        existing_autoincrement=column.get("autoincrement"),
    )


def _normalize_datetime_defaults(table_name: str) -> None:
    """Repair defaults when a previous attempt already renamed a column."""
    columns = _columns(table_name)
    for column_name in ("dtacriacao", "dtaatualizacao"):
        column = columns.get(column_name)
        if column is None:
            continue
        datetime_default = _datetime_default(column_name)
        op.alter_column(
            table_name,
            column_name,
            existing_type=column["type"],
            existing_nullable=column.get("nullable", True),
            existing_server_default=datetime_default,
            server_default=datetime_default,
        )


def upgrade() -> None:
    for table_name, renames in RENAMES.items():
        for new_name, old_names in renames.items():
            _rename(table_name, old_names, new_name)
        _normalize_datetime_defaults(table_name)


def downgrade() -> None:
    for table_name, renames in reversed(tuple(RENAMES.items())):
        for new_name, old_names in reversed(tuple(renames.items())):
            _rename(table_name, (new_name,), old_names[0])
