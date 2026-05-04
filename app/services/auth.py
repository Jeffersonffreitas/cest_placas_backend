from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.users import create_user, get_user_by_username


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    user = get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise AppException(
            "Invalid username or password.",
            status_code=401,
            code="invalid_credentials",
        )

    if not user.is_active:
        raise AppException(
            "User is inactive.",
            status_code=403,
            code="inactive_user",
        )

    return user


def ensure_default_admin(db: Session) -> User:
    user = get_user_by_username(db, settings.admin_username)
    if user is not None:
        return user

    return create_user(
        db,
        username=settings.admin_username,
        password_hash=get_password_hash(settings.admin_password),
        full_name="Administrador",
        is_active=True,
        is_superuser=True,
    )
