"""Consolidate students in people and remove the legacy physical structures.

Revision ID: 0018_remove_legacy_students
Revises: 0017_access_points_cameras
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0018_remove_legacy_students"
down_revision: str | None = "0017_access_points_cameras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STUDENTS = "tblalunos"
PEOPLE = "tblpessoas"
EVENTS = "tbleventosacesso"
LEGACY_EVENT_COLUMN = "intalunoid"

SQLITE_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _abort(message: str) -> None:
    raise RuntimeError(f"Phase 6.10 safety check failed: {message}")


def _bind():
    return op.get_bind()


def _inspector():
    return inspect(_bind())


def _table_exists(table_name: str) -> bool:
    inspector = _inspector()
    return table_name in inspector.get_table_names() or inspector.has_table(table_name)


def _columns(table_name: str) -> dict[str, dict]:
    if not _table_exists(table_name):
        return {}
    return {column["name"]: column for column in _inspector().get_columns(table_name)}


def _reflected_table(table_name: str) -> sa.Table:
    return sa.Table(table_name, sa.MetaData(), autoload_with=_bind())


def _first_column(columns: dict[str, dict], *candidates: str) -> str | None:
    return next((candidate for candidate in candidates if candidate in columns), None)


def _require_primary_schema() -> None:
    if not _table_exists(PEOPLE):
        _abort(f"required table {PEOPLE!r} does not exist")
    if not _table_exists(EVENTS):
        _abort(f"required table {EVENTS!r} does not exist")

    required_people = {
        "intpessoaid",
        "strtipopessoa",
        "strmatricula",
        "strnomecompleto",
        "stremail",
        "strtelefone",
        "bolativo",
        "dtacriacao",
        "dtaatualizacao",
    }
    missing_people = required_people - set(_columns(PEOPLE))
    if missing_people:
        _abort(
            f"{PEOPLE} is missing required columns: "
            f"{', '.join(sorted(missing_people))}"
        )

    event_columns = _columns(EVENTS)
    if "intpessoaid" not in event_columns:
        _abort(f"{EVENTS}.intpessoaid does not exist")


def _legacy_student_layout() -> dict[str, str]:
    columns = _columns(STUDENTS)
    layout = {
        "id": _first_column(columns, "intalunoid", "numalunoid", "IntAlunoid", "NumAlunoid"),
        "registration": _first_column(columns, "strmatricula", "StrMatricula"),
        "full_name": _first_column(columns, "strnomecompleto", "StrNomeCompleto"),
        "email": _first_column(columns, "stremail", "StrEmail"),
        "phone": _first_column(columns, "strtelefone", "StrTelefone"),
        "active": _first_column(columns, "bolativo", "IntAtivo", "IntIsActive"),
        "created_at": _first_column(columns, "dtacriacao", "DtdCriacao", "DtdCreatedAt"),
        "updated_at": _first_column(columns, "dtaatualizacao", "DtdAtualizacao", "DtdUpdatedAt"),
    }
    required = (
        "id",
        "registration",
        "full_name",
        "email",
        "phone",
        "active",
        "created_at",
        "updated_at",
    )
    missing = [name for name in required if layout[name] is None]
    if missing:
        _abort(
            f"cannot safely read {STUDENTS}; missing semantic columns: "
            f"{', '.join(missing)}"
        )
    return {key: value for key, value in layout.items() if value is not None}


def _unexpected_legacy_columns() -> list[str]:
    allowed = {
        (STUDENTS, "intalunoid"),
        (STUDENTS, "numalunoid"),
        (EVENTS, LEGACY_EVENT_COLUMN),
    }
    unexpected: list[str] = []
    for table_name in _inspector().get_table_names():
        for column in _inspector().get_columns(table_name):
            column_name = str(column["name"])
            if column_name.lower() not in {"intalunoid", "numalunoid", "student_id"}:
                continue
            if (table_name, column_name.lower()) not in allowed:
                unexpected.append(f"{table_name}.{column_name}")
    return sorted(unexpected)


def _student_rows(layout: dict[str, str]) -> list[dict[str, object]]:
    table = _reflected_table(STUDENTS)
    statement = sa.select(table).order_by(table.c[layout["id"]])
    return [dict(row) for row in _bind().execute(statement).mappings().all()]


def _matching_student_people(registration: str) -> list[dict[str, object]]:
    people = _reflected_table(PEOPLE)
    statement = (
        sa.select(people.c.intpessoaid, people.c.strtipopessoa)
        .where(
            people.c.strmatricula == registration,
            people.c.strtipopessoa == "ALUNO",
        )
        .order_by(people.c.intpessoaid)
    )
    return [dict(row) for row in _bind().execute(statement).mappings().all()]


def _insert_person_from_student(
    student: dict[str, object], layout: dict[str, str]
) -> None:
    registration = student[layout["registration"]]
    full_name = student[layout["full_name"]]
    if not isinstance(registration, str) or not registration.strip():
        _abort(
            f"legacy student {student[layout['id']]} has no usable registration"
        )
    if not isinstance(full_name, str) or not full_name.strip():
        _abort(
            f"legacy student {student[layout['id']]} has no usable full name"
        )

    person_columns = _columns(PEOPLE)
    values: dict[str, object] = {
        "strtipopessoa": "ALUNO",
        "strmatricula": registration,
        "strnomecompleto": full_name,
    }
    compatible_fields = {
        "email": "stremail",
        "phone": "strtelefone",
        "active": "bolativo",
        "created_at": "dtacriacao",
        "updated_at": "dtaatualizacao",
    }
    for logical_name, person_column in compatible_fields.items():
        student_column = layout.get(logical_name)
        if student_column is None or person_column not in person_columns:
            continue
        value = student[student_column]
        if value is not None:
            values[person_column] = value

    people = _reflected_table(PEOPLE)
    _bind().execute(sa.insert(people).values(**values))


def _migrate_and_map_students() -> dict[int, int]:
    if not _table_exists(STUDENTS):
        return {}
    layout = _legacy_student_layout()
    mapping: dict[int, int] = {}
    legacy_registrations: dict[str, int] = {}
    for student in _student_rows(layout):
        legacy_id = int(student[layout["id"]])
        registration_value = student[layout["registration"]]
        if not isinstance(registration_value, str) or not registration_value.strip():
            _abort(f"legacy student {legacy_id} has no usable registration")
        previous_id = legacy_registrations.get(registration_value)
        if previous_id is not None:
            _abort(
                f"legacy students {previous_id} and {legacy_id} share registration "
                f"{registration_value!r}"
            )
        legacy_registrations[registration_value] = legacy_id

        matches = _matching_student_people(registration_value)
        if len(matches) > 1:
            _abort(
                f"legacy student {legacy_id} registration {registration_value!r} "
                "matches multiple ALUNO people"
            )
        if not matches:
            _insert_person_from_student(student, layout)
            matches = _matching_student_people(registration_value)
        if len(matches) != 1:
            _abort(
                f"legacy student {legacy_id} registration {registration_value!r} "
                "could not be represented by exactly one ALUNO person"
            )
        mapping[legacy_id] = int(matches[0]["intpessoaid"])
    return mapping


def _validate_all_students_preserved(mapping: dict[int, int]) -> None:
    if not _table_exists(STUDENTS):
        return
    layout = _legacy_student_layout()
    rows = _student_rows(layout)
    for student in rows:
        legacy_id = int(student[layout["id"]])
        registration = student[layout["registration"]]
        matches = (
            _matching_student_people(registration)
            if isinstance(registration, str)
            else []
        )
        if len(matches) != 1 or mapping.get(legacy_id) != int(matches[0]["intpessoaid"]):
            _abort(f"legacy student {legacy_id} is not safely preserved in {PEOPLE}")


def _validate_and_backfill_events(student_mapping: dict[int, int]) -> None:
    event_columns = _columns(EVENTS)
    if LEGACY_EVENT_COLUMN not in event_columns:
        return
    if "inteventoacessoid" not in event_columns:
        _abort(f"{EVENTS} has no event identifier for conflict reporting")

    events = _reflected_table(EVENTS)
    rows = _bind().execute(
        sa.select(
            events.c.inteventoacessoid,
            events.c.intalunoid,
            events.c.intpessoaid,
        )
        .where(events.c.intalunoid.is_not(None))
        .order_by(events.c.inteventoacessoid)
    ).mappings().all()

    updates: list[tuple[int, int]] = []
    for row in rows:
        event_id = int(row["inteventoacessoid"])
        legacy_student_id = int(row["intalunoid"])
        expected_person_id = student_mapping.get(legacy_student_id)
        if expected_person_id is None:
            if not _table_exists(STUDENTS):
                _abort(
                    f"event {event_id} references legacy student {legacy_student_id}, "
                    f"but {STUDENTS} no longer exists"
                )
            _abort(
                f"event {event_id} references unknown legacy student "
                f"{legacy_student_id}"
            )
        current_person_id = row["intpessoaid"]
        if current_person_id is None:
            updates.append((event_id, expected_person_id))
        elif int(current_person_id) != expected_person_id:
            _abort(
                f"event {event_id} points to person {current_person_id}, but legacy "
                f"student {legacy_student_id} maps to person {expected_person_id}"
            )

    for event_id, person_id in updates:
        _bind().execute(
            sa.update(events)
            .where(events.c.inteventoacessoid == event_id)
            .values(intpessoaid=person_id)
        )

    remaining = _bind().execute(
        sa.select(sa.func.count())
        .select_from(events)
        .where(
            events.c.intalunoid.is_not(None),
            events.c.intpessoaid.is_(None),
        )
    ).scalar_one()
    if int(remaining) != 0:
        _abort(f"{remaining} events still depend exclusively on intalunoid")


def _foreign_keys_to_students() -> list[tuple[str, dict]]:
    references: list[tuple[str, dict]] = []
    for table_name in _inspector().get_table_names():
        for foreign_key in _inspector().get_foreign_keys(table_name):
            if str(foreign_key.get("referred_table") or "").lower() == STUDENTS:
                references.append((table_name, foreign_key))
    return references


def _expected_event_foreign_keys() -> list[dict]:
    expected: list[dict] = []
    unexpected: list[str] = []
    for table_name, foreign_key in _foreign_keys_to_students():
        constrained = [str(name).lower() for name in foreign_key.get("constrained_columns") or []]
        referred = [str(name).lower() for name in foreign_key.get("referred_columns") or []]
        if (
            table_name == EVENTS
            and constrained == [LEGACY_EVENT_COLUMN]
            and referred in (["intalunoid"], ["numalunoid"])
        ):
            expected.append(foreign_key)
            continue
        name = foreign_key.get("name") or "<unnamed>"
        unexpected.append(f"{table_name}.{name}({', '.join(constrained)})")
    if unexpected:
        _abort(
            f"unexpected foreign keys still reference {STUDENTS}: "
            f"{'; '.join(sorted(unexpected))}"
        )
    return expected


def _legacy_event_indexes() -> list[str]:
    if LEGACY_EVENT_COLUMN not in _columns(EVENTS):
        return []
    return [
        str(index["name"])
        for index in _inspector().get_indexes(EVENTS)
        if LEGACY_EVENT_COLUMN
        in [str(name).lower() for name in index.get("column_names") or []]
        and index.get("name")
    ]


def _drop_legacy_event_column(foreign_keys: list[dict]) -> None:
    if LEGACY_EVENT_COLUMN not in _columns(EVENTS):
        return
    indexes = _legacy_event_indexes()
    if _bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            EVENTS,
            recreate="always",
            naming_convention=SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            for foreign_key in foreign_keys:
                name = foreign_key.get("name")
                if not name:
                    name = f"fk_{EVENTS}_{LEGACY_EVENT_COLUMN}_{STUDENTS}"
                batch_op.drop_constraint(str(name), type_="foreignkey")
            for index_name in indexes:
                batch_op.drop_index(index_name)
            batch_op.drop_column(LEGACY_EVENT_COLUMN)
    else:
        for foreign_key in foreign_keys:
            name = foreign_key.get("name")
            if not name:
                _abort(
                    f"cannot safely drop an unnamed foreign key from {EVENTS} "
                    f"to {STUDENTS}"
                )
            op.drop_constraint(str(name), EVENTS, type_="foreignkey")
        for index_name in indexes:
            op.drop_index(index_name, table_name=EVENTS)
        if LEGACY_EVENT_COLUMN in _columns(EVENTS):
            op.drop_column(EVENTS, LEGACY_EVENT_COLUMN)

    if LEGACY_EVENT_COLUMN in _columns(EVENTS):
        _abort(f"failed to remove {EVENTS}.{LEGACY_EVENT_COLUMN}")


def _drop_students_table(student_mapping: dict[int, int]) -> None:
    if not _table_exists(STUDENTS):
        return
    _validate_all_students_preserved(student_mapping)
    references = _foreign_keys_to_students()
    if references:
        formatted = "; ".join(
            f"{table}.{foreign_key.get('name') or '<unnamed>'}"
            for table, foreign_key in references
        )
        _abort(f"foreign keys still reference {STUDENTS}: {formatted}")
    op.drop_table(STUDENTS)


def upgrade() -> None:
    _require_primary_schema()
    unexpected_columns = _unexpected_legacy_columns()
    if unexpected_columns:
        _abort(
            "unexpected legacy student columns exist: "
            f"{', '.join(unexpected_columns)}"
        )

    expected_foreign_keys = _expected_event_foreign_keys()
    student_mapping = _migrate_and_map_students()
    _validate_all_students_preserved(student_mapping)
    _validate_and_backfill_events(student_mapping)

    # MySQL/MariaDB auto-commits each DDL statement. Every operation below is
    # preceded by live-schema checks so a rerun can continue after interruption.
    _drop_legacy_event_column(expected_foreign_keys)
    _drop_students_table(student_mapping)


def downgrade() -> None:
    raise RuntimeError(
        "0018_remove_legacy_students is irreversible: original tblalunos IDs "
        "and row history cannot be reconstructed safely from tblpessoas"
    )
