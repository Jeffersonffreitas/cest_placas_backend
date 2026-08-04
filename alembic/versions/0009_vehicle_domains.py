"""Reference vehicle brand, model and color domains without removing legacy text.

Revision ID: 0009_vehicle_domains
Revises: 0008_create_domains
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0009_vehicle_domains"
down_revision: str | None = "0008_create_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VEHICLES = "tblveiculos"
DOMAINS = "tbldominios"
FIELDS = (
    ("strmarca", "nummarcaid", "MARCA_VEICULO"),
    ("strmodelo", "nummodeloid", "MODELO_VEICULO"),
    ("strcor", "numcorid", "COR_VEICULO"),
)
INDEXES = (
    ("idx_tblveiculos_nummarcaid", "nummarcaid"),
    ("idx_tblveiculos_nummodeloid", "nummodeloid"),
    ("idx_tblveiculos_numcorid", "numcorid"),
)
FOREIGN_KEYS = (
    ("fk_tblveiculos_marca", "nummarcaid"),
    ("fk_tblveiculos_modelo", "nummodeloid"),
    ("fk_tblveiculos_cor", "numcorid"),
)


def _inspector():
    return inspect(op.get_bind())


def _columns(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes() -> set[str]:
    if not _inspector().has_table(VEHICLES):
        return set()
    return {index["name"] for index in _inspector().get_indexes(VEHICLES)}


def _foreign_keys() -> tuple[set[str], set[tuple[tuple[str, ...], str, tuple[str, ...]]]]:
    if not _inspector().has_table(VEHICLES):
        return set(), set()
    foreign_keys = _inspector().get_foreign_keys(VEHICLES)
    names = {fk["name"] for fk in foreign_keys if fk.get("name")}
    signatures = {
        (
            tuple(fk.get("constrained_columns") or ()),
            str(fk.get("referred_table") or ""),
            tuple(fk.get("referred_columns") or ()),
        )
        for fk in foreign_keys
    }
    return names, signatures


def _has_orphan_references(column_name: str) -> bool:
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {VEHICLES} vehicle
            LEFT JOIN {DOMAINS} domain_row
              ON domain_row.numdominioid = vehicle.{column_name}
            WHERE vehicle.{column_name} IS NOT NULL
              AND domain_row.numdominioid IS NULL
            """
        )
    )
    return int(result.scalar_one()) > 0


def _backfill(text_column: str, id_column: str, domain_type: str) -> None:
    bind = op.get_bind()
    params = {"domain_type": domain_type}
    bind.execute(
        sa.text(
            f"""
            INSERT INTO {DOMAINS} (strtipo, strcodigo, strnome, bolativo, dtacriacao, dtaatualizacao)
            SELECT :domain_type, NULL, source.strnome, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM (
                SELECT DISTINCT TRIM({text_column}) AS strnome
                FROM {VEHICLES}
                WHERE {text_column} IS NOT NULL AND TRIM({text_column}) <> ''
            ) AS source
            WHERE NOT EXISTS (
                SELECT 1 FROM {DOMAINS} domain_row
                WHERE domain_row.strtipo = :domain_type AND domain_row.strnome = source.strnome
            )
            """
        ),
        params,
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE {VEHICLES}
            SET {id_column} = (
                SELECT MIN(domain_row.numdominioid)
                FROM {DOMAINS} domain_row
                WHERE domain_row.strtipo = :domain_type
                  AND domain_row.strnome = TRIM({VEHICLES}.{text_column})
            )
            WHERE {id_column} IS NULL
              AND {text_column} IS NOT NULL
              AND TRIM({text_column}) <> ''
            """
        ),
        params,
    )


def upgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table(VEHICLES) or not inspector.has_table(DOMAINS):
        return

    for column_name in ("nummarcaid", "nummodeloid", "numcorid"):
        if column_name not in _columns(VEHICLES):
            op.add_column(VEHICLES, sa.Column(column_name, sa.Integer(), nullable=True))

    vehicle_columns = _columns(VEHICLES)
    domain_columns = _columns(DOMAINS)
    required_domain_columns = {
        "numdominioid", "strtipo", "strcodigo", "strnome", "bolativo",
        "dtacriacao", "dtaatualizacao",
    }
    if required_domain_columns.issubset(domain_columns):
        for text_column, id_column, domain_type in FIELDS:
            if text_column in vehicle_columns and id_column in vehicle_columns:
                _backfill(text_column, id_column, domain_type)

    indexes = _indexes()
    for index_name, column_name in INDEXES:
        if column_name in vehicle_columns and index_name not in indexes:
            op.create_index(index_name, VEHICLES, [column_name], unique=False)
            indexes.add(index_name)

    foreign_key_names, foreign_key_signatures = _foreign_keys()
    if "numdominioid" in domain_columns:
        for fk_name, column_name in FOREIGN_KEYS:
            signature = ((column_name,), DOMAINS, ("numdominioid",))
            if (
                column_name in vehicle_columns
                and fk_name not in foreign_key_names
                and signature not in foreign_key_signatures
                and not _has_orphan_references(column_name)
            ):
                op.create_foreign_key(
                    fk_name, VEHICLES, DOMAINS, [column_name], ["numdominioid"],
                    ondelete="RESTRICT",
                )
                foreign_key_names.add(fk_name)
                foreign_key_signatures.add(signature)


def downgrade() -> None:
    # Intentionally non-destructive: legacy text and structured references are retained.
    pass
