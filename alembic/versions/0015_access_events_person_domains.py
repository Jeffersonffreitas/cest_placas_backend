"""Resolve access events through vehicle, person and operational domains.

Revision ID: 0015_access_events_person_domains
Revises: 0014_remove_vehicle_student_dependency
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0015_access_events_person_domains"
down_revision: str | None = "0014_remove_vehicle_student_dependency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENTS = "tbleventosacesso"
DOMAINS = "tbldominios"

EVENT_COLUMNS = (
    ("intveiculoid", sa.Integer()),
    ("intpessoaid", sa.Integer()),
    ("intleituraplacaid", sa.Integer()),
    ("intacaoid", sa.Integer()),
    ("intorigemid", sa.Integer()),
    ("strsituacao", sa.String(length=30)),
    ("strplacaentrada", sa.String(length=20)),
    ("strplacanormalizada", sa.String(length=10)),
    ("strorigem", sa.String(length=30)),
    ("dtacriacao", sa.DateTime()),
)

INDEXES = (
    ("ix_tbleventosacesso_veiculo", "intveiculoid"),
    ("ix_tbleventosacesso_pessoa", "intpessoaid"),
    ("ix_tbleventosacesso_leituraplaca", "intleituraplacaid"),
    ("ix_tbleventosacesso_acao", "intacaoid"),
    ("ix_tbleventosacesso_origem_id", "intorigemid"),
    ("ix_tbleventosacesso_placa_normalizada", "strplacanormalizada"),
    ("ix_tbleventosacesso_origem", "strorigem"),
    ("ix_tbleventosacesso_situacao", "strsituacao"),
    ("ix_tbleventosacesso_criacao", "dtacriacao"),
)

FOREIGN_KEYS = (
    ("fk_tbleventosacesso_veiculo", "intveiculoid", "tblveiculos", "intveiculoid", "SET NULL"),
    ("fk_tbleventosacesso_pessoa", "intpessoaid", "tblpessoas", "intpessoaid", "SET NULL"),
    ("fk_tbleventosacesso_leituraplaca", "intleituraplacaid", "tblleiturasplacas", "intleituraplacaid", "SET NULL"),
    ("fk_tbleventosacesso_acao", "intacaoid", DOMAINS, "intdominioid", "RESTRICT"),
    ("fk_tbleventosacesso_origem", "intorigemid", DOMAINS, "intdominioid", "RESTRICT"),
)

DOMAIN_VALUES = {
    "ACAO_ACESSO": ("ENTRADA", "SAIDA", "TENTATIVA", "LIBERACAO_MANUAL", "BLOQUEIO"),
    "ORIGEM_ACESSO": (
        "PORTAO_PRINCIPAL",
        "PORTAO_FUNDOS",
        "GUARITA",
        "TESTE_MANUAL",
        "UPLOAD_IMAGEM",
    ),
}


def _inspector():
    return inspect(op.get_bind())


def _tables() -> set[str]:
    return set(_inspector().get_table_names())


def _columns(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {column["name"] for column in _inspector().get_columns(table)}


def _add_missing_columns() -> None:
    if EVENTS not in _tables():
        return
    columns = _columns(EVENTS)
    for name, column_type in EVENT_COLUMNS:
        if name in columns:
            continue
        kwargs: dict[str, object] = {"nullable": True}
        if name == "strorigem":
            kwargs["server_default"] = "manual"
        if name == "dtacriacao":
            kwargs["server_default"] = sa.text("CURRENT_TIMESTAMP")
        op.add_column(EVENTS, sa.Column(name, column_type, **kwargs))
        columns.add(name)

    if "strsituacao" in columns and op.get_bind().dialect.name in {"mysql", "mariadb"}:
        op.alter_column(
            EVENTS,
            "strsituacao",
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
        )


def _backfill_people() -> None:
    required = {EVENTS, "tblalunos", "tblpessoas"}
    if not required.issubset(_tables()):
        return
    if "intalunoid" not in _columns(EVENTS) or "intpessoaid" not in _columns(EVENTS):
        return
    if op.get_bind().dialect.name in {"mysql", "mariadb"}:
        op.execute(sa.text("""
            UPDATE tbleventosacesso event_row
            JOIN tblalunos student ON student.intalunoid = event_row.intalunoid
            JOIN tblpessoas person
              ON person.strtipopessoa = 'ALUNO'
             AND person.strmatricula = student.strmatricula
            SET event_row.intpessoaid = person.intpessoaid
            WHERE event_row.intpessoaid IS NULL
        """))
    else:
        op.execute(sa.text("""
            UPDATE tbleventosacesso
            SET intpessoaid = (
                SELECT MIN(person.intpessoaid)
                FROM tblalunos student
                JOIN tblpessoas person
                  ON person.strtipopessoa = 'ALUNO'
                 AND person.strmatricula = student.strmatricula
                WHERE student.intalunoid = tbleventosacesso.intalunoid
            )
            WHERE intpessoaid IS NULL AND intalunoid IS NOT NULL
        """))


def _create_indexes() -> None:
    if EVENTS not in _tables():
        return
    columns = _columns(EVENTS)
    indexes = {index["name"] for index in _inspector().get_indexes(EVENTS)}
    for name, column in INDEXES:
        if column in columns and name not in indexes:
            op.create_index(name, EVENTS, [column], unique=False)
            indexes.add(name)


def _create_foreign_keys() -> None:
    if EVENTS not in _tables() or op.get_bind().dialect.name not in {"mysql", "mariadb"}:
        return
    event_columns = _columns(EVENTS)
    existing = _inspector().get_foreign_keys(EVENTS)
    names = {fk.get("name") for fk in existing}
    signatures = {
        (tuple(fk.get("constrained_columns") or ()), fk.get("referred_table"), tuple(fk.get("referred_columns") or ()))
        for fk in existing
    }
    for name, column, target, target_column, ondelete in FOREIGN_KEYS:
        signature = ((column,), target, (target_column,))
        if (
            column in event_columns
            and target_column in _columns(target)
            and name not in names
            and signature not in signatures
        ):
            op.create_foreign_key(name, EVENTS, target, [column], [target_column], ondelete=ondelete)
            names.add(name)
            signatures.add(signature)


def _seed_domains() -> None:
    required = {"intdominioid", "strtipo", "strcodigo", "strnome", "bolativo"}
    if DOMAINS not in _tables() or not required.issubset(_columns(DOMAINS)):
        return
    bind = op.get_bind()
    for domain_type, codes in DOMAIN_VALUES.items():
        for code in codes:
            existing_id = bind.execute(
                sa.text(
                    "SELECT MIN(intdominioid) FROM tbldominios "
                    "WHERE strtipo = :domain_type "
                    "AND (strcodigo = :code OR UPPER(REPLACE(strnome, ' ', '_')) = :code)"
                ),
                {"domain_type": domain_type, "code": code},
            ).scalar_one_or_none()
            if existing_id is None:
                bind.execute(
                    sa.text(
                        "INSERT INTO tbldominios "
                        "(strtipo, strcodigo, strnome, bolativo, dtacriacao, dtaatualizacao) "
                        "VALUES (:domain_type, :code, :name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ),
                    {"domain_type": domain_type, "code": code, "name": code.replace("_", " ").title()},
                )
            else:
                bind.execute(
                    sa.text("UPDATE tbldominios SET bolativo = 1 WHERE intdominioid = :domain_id"),
                    {"domain_id": existing_id},
                )


def upgrade() -> None:
    _add_missing_columns()
    _backfill_people()
    _create_indexes()
    _create_foreign_keys()
    _seed_domains()


def downgrade() -> None:
    # Non-destructive by project policy: columns, links and seeded domains are retained.
    pass
