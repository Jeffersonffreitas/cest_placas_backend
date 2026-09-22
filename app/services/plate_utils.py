import re

from app.core.exceptions import AppException


_PLATE_CLEANER = re.compile(r"[^A-Za-z0-9]")
_BR_PLATE_PATTERN = re.compile(r"^[A-Z]{3}(?:[0-9]{4}|[0-9][A-Z][0-9]{2})$")


def normalize_plate(plate: str) -> str:
    return _PLATE_CLEANER.sub("", plate).upper()


def normalize_and_validate_plate(plate: str) -> str:
    normalized_plate = normalize_plate(plate)
    if _BR_PLATE_PATTERN.fullmatch(normalized_plate) is None:
        raise AppException(
            "Plate must match a valid Brazilian plate pattern.",
            status_code=400,
            code="invalid_plate",
            details={"operational_decision": "PLACA_INVALIDA"},
        )
    return normalized_plate
