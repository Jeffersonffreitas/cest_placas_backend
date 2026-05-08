import re

from app.core.exceptions import AppException


_PLATE_CLEANER = re.compile(r"[^A-Za-z0-9]")


def normalize_plate(plate: str) -> str:
    return _PLATE_CLEANER.sub("", plate).upper()


def normalize_and_validate_plate(plate: str) -> str:
    normalized_plate = normalize_plate(plate)
    if len(normalized_plate) != 7 or not normalized_plate.isalnum():
        raise AppException(
            "Plate must have 7 alphanumeric characters.",
            status_code=400,
            code="invalid_plate",
        )
    return normalized_plate
