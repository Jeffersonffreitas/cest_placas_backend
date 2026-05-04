import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppException


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260_000


class InvalidTokenError(Exception):
    pass


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def get_password_hash(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}$"
        f"{salt}${_base64url_encode(password_hash)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, stored_hash = password_hash.split("$", maxsplit=3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return secrets.compare_digest(_base64url_encode(computed_hash), stored_hash)
    except (TypeError, ValueError):
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    if settings.jwt_algorithm != "HS256":
        raise ValueError("Only HS256 JWT tokens are supported.")

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()

        if not secrets.compare_digest(
            _base64url_encode(expected_signature),
            encoded_signature,
        ):
            raise InvalidTokenError

        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))

        if header.get("alg") != settings.jwt_algorithm:
            raise InvalidTokenError

        expires_at = payload.get("exp")
        if expires_at is None or int(expires_at) < int(datetime.now(timezone.utc).timestamp()):
            raise InvalidTokenError

        return payload
    except (ValueError, json.JSONDecodeError, TypeError):
        raise InvalidTokenError from None


def verify_admin_credentials(username: str, password: str) -> None:
    valid_username = secrets.compare_digest(username, settings.admin_username)
    valid_password = secrets.compare_digest(password, settings.admin_password)

    if not (valid_username and valid_password):
        raise AppException(
            "Invalid administrative credentials.",
            status_code=401,
            code="invalid_credentials",
        )
