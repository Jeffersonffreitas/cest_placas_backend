import secrets

from app.core.config import settings
from app.core.exceptions import AppException


def verify_admin_credentials(username: str, password: str) -> None:
    valid_username = secrets.compare_digest(username, settings.admin_username)
    valid_password = secrets.compare_digest(password, settings.admin_password)

    if not (valid_username and valid_password):
        raise AppException(
            "Invalid administrative credentials.",
            status_code=401,
            code="invalid_credentials",
        )

