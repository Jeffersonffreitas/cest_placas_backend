"""rename domain columns to faculty standard

Revision ID: 0005_rename_domain_columns_faculty_standard
Revises: 0004_access_event_source_index
Create Date: 2026-06-12 15:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0005_rename_domain_columns_faculty_standard"
down_revision: Union[str, None] = "0004_access_event_source_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _table_columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _foreign_key_exists(table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    expected_name = str(constraint_name)
    return any(
        foreign_key["name"] == expected_name
        for foreign_key in inspect(op.get_bind()).get_foreign_keys(table_name)
    )


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


def upgrade() -> None:
    _drop_foreign_key_if_exists("access_events", "fk_access_events_vehicle_id_vehicles")
    _drop_foreign_key_if_exists("access_events", "fk_access_events_student_id_students")
    _drop_foreign_key_if_exists("plate_reads", "fk_plate_reads_vehicle_id_vehicles")
    _drop_foreign_key_if_exists("vehicles", "fk_vehicles_student_id_students")

    _rename_column("students", "id", "IntStudentid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("students", "registration_number", "StrRegistrationNumber", sa.String(length=50), existing_nullable=False)
    _rename_column("students", "full_name", "StrFullName", sa.String(length=255), existing_nullable=False)
    _rename_column("students", "email", "StrEmail", sa.String(length=255), existing_nullable=True)
    _rename_column("students", "phone", "StrPhone", sa.String(length=20), existing_nullable=True)
    _rename_column("students", "is_active", "IntIsActive", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column(
        "students",
        "created_at",
        "DtdCreatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column(
        "students",
        "updated_at",
        "DtdUpdatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    _rename_column("vehicles", "id", "IntVehicleid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("vehicles", "student_id", "IntStudentid", sa.Integer(), existing_nullable=False)
    _rename_column("vehicles", "plate", "StrPlate", sa.String(length=10), existing_nullable=False)
    _rename_column("vehicles", "brand", "StrBrand", sa.String(length=100), existing_nullable=True)
    _rename_column("vehicles", "model", "StrModel", sa.String(length=100), existing_nullable=True)
    _rename_column("vehicles", "color", "StrColor", sa.String(length=50), existing_nullable=True)
    _rename_column("vehicles", "is_active", "IntIsActive", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column(
        "vehicles",
        "created_at",
        "DtdCreatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column(
        "vehicles",
        "updated_at",
        "DtdUpdatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    _rename_column("plate_reads", "id", "IntPlateReadid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("plate_reads", "vehicle_id", "IntVehicleid", sa.Integer(), existing_nullable=True)
    _rename_column("plate_reads", "plate", "StrPlate", sa.String(length=10), existing_nullable=False)
    _rename_column(
        "plate_reads",
        "source",
        "StrSource",
        sa.String(length=30),
        existing_nullable=False,
        existing_server_default="manual",
    )
    _rename_column("plate_reads", "confidence", "DecConfidence", sa.Numeric(precision=5, scale=2), existing_nullable=True)
    _rename_column("plate_reads", "image_path", "StrImagePath", sa.String(length=255), existing_nullable=True)
    _rename_column("plate_reads", "read_at", "DtdReadAt", sa.DateTime(), existing_nullable=False)
    _rename_column(
        "plate_reads",
        "created_at",
        "DtdCreatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column(
        "plate_reads",
        "updated_at",
        "DtdUpdatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    _rename_column("access_events", "id", "IntAccessEventid", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("access_events", "vehicle_id", "IntVehicleid", sa.Integer(), existing_nullable=True)
    _rename_column("access_events", "student_id", "IntStudentid", sa.Integer(), existing_nullable=True)
    _rename_column("access_events", "status", "StrStatus", sa.String(length=20), existing_nullable=False)
    _rename_column(
        "access_events",
        "created_at",
        "DtdCreatedAt",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column("access_events", "plate_input", "StrPlateInput", sa.String(length=20), existing_nullable=False)
    _rename_column("access_events", "plate_normalized", "StrPlateNormalized", sa.String(length=10), existing_nullable=False)
    _rename_column(
        "access_events",
        "source",
        "StrSource",
        sa.String(length=30),
        existing_nullable=False,
        existing_server_default="manual",
    )

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


def downgrade() -> None:
    _drop_foreign_key_if_exists("access_events", "fk_access_events_vehicle_id_vehicles")
    _drop_foreign_key_if_exists("access_events", "fk_access_events_student_id_students")
    _drop_foreign_key_if_exists("plate_reads", "fk_plate_reads_vehicle_id_vehicles")
    _drop_foreign_key_if_exists("vehicles", "fk_vehicles_student_id_students")

    _rename_column("access_events", "IntAccessEventid", "id", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("access_events", "IntVehicleid", "vehicle_id", sa.Integer(), existing_nullable=True)
    _rename_column("access_events", "IntStudentid", "student_id", sa.Integer(), existing_nullable=True)
    _rename_column("access_events", "StrStatus", "status", sa.String(length=20), existing_nullable=False)
    _rename_column(
        "access_events",
        "DtdCreatedAt",
        "created_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column("access_events", "StrPlateInput", "plate_input", sa.String(length=20), existing_nullable=False)
    _rename_column("access_events", "StrPlateNormalized", "plate_normalized", sa.String(length=10), existing_nullable=False)
    _rename_column(
        "access_events",
        "StrSource",
        "source",
        sa.String(length=30),
        existing_nullable=False,
        existing_server_default="manual",
    )

    _rename_column("plate_reads", "IntPlateReadid", "id", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("plate_reads", "IntVehicleid", "vehicle_id", sa.Integer(), existing_nullable=True)
    _rename_column("plate_reads", "StrPlate", "plate", sa.String(length=10), existing_nullable=False)
    _rename_column(
        "plate_reads",
        "StrSource",
        "source",
        sa.String(length=30),
        existing_nullable=False,
        existing_server_default="manual",
    )
    _rename_column("plate_reads", "DecConfidence", "confidence", sa.Numeric(precision=5, scale=2), existing_nullable=True)
    _rename_column("plate_reads", "StrImagePath", "image_path", sa.String(length=255), existing_nullable=True)
    _rename_column("plate_reads", "DtdReadAt", "read_at", sa.DateTime(), existing_nullable=False)
    _rename_column(
        "plate_reads",
        "DtdCreatedAt",
        "created_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column(
        "plate_reads",
        "DtdUpdatedAt",
        "updated_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    _rename_column("vehicles", "IntVehicleid", "id", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("vehicles", "IntStudentid", "student_id", sa.Integer(), existing_nullable=False)
    _rename_column("vehicles", "StrPlate", "plate", sa.String(length=10), existing_nullable=False)
    _rename_column("vehicles", "StrBrand", "brand", sa.String(length=100), existing_nullable=True)
    _rename_column("vehicles", "StrModel", "model", sa.String(length=100), existing_nullable=True)
    _rename_column("vehicles", "StrColor", "color", sa.String(length=50), existing_nullable=True)
    _rename_column("vehicles", "IntIsActive", "is_active", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column(
        "vehicles",
        "DtdCreatedAt",
        "created_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column(
        "vehicles",
        "DtdUpdatedAt",
        "updated_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    _rename_column("students", "IntStudentid", "id", sa.Integer(), existing_nullable=False, existing_autoincrement=True)
    _rename_column("students", "StrRegistrationNumber", "registration_number", sa.String(length=50), existing_nullable=False)
    _rename_column("students", "StrFullName", "full_name", sa.String(length=255), existing_nullable=False)
    _rename_column("students", "StrEmail", "email", sa.String(length=255), existing_nullable=True)
    _rename_column("students", "StrPhone", "phone", sa.String(length=20), existing_nullable=True)
    _rename_column("students", "IntIsActive", "is_active", sa.Boolean(), existing_nullable=False, existing_server_default="1")
    _rename_column(
        "students",
        "DtdCreatedAt",
        "created_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    _rename_column(
        "students",
        "DtdUpdatedAt",
        "updated_at",
        sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    _create_foreign_key_if_missing(
        "fk_vehicles_student_id_students",
        "vehicles",
        "students",
        ["student_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    _create_foreign_key_if_missing(
        "fk_plate_reads_vehicle_id_vehicles",
        "plate_reads",
        "vehicles",
        ["vehicle_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_access_events_student_id_students",
        "access_events",
        "students",
        ["student_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _create_foreign_key_if_missing(
        "fk_access_events_vehicle_id_vehicles",
        "access_events",
        "vehicles",
        ["vehicle_id"],
        ["id"],
        ondelete="SET NULL",
    )
