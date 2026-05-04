from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import InvalidTokenError, decode_access_token
from app.db.deps import get_db
from app.models.user import User
from app.repositories.users import get_user_by_username


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not isinstance(username, str):
            raise InvalidTokenError
    except InvalidTokenError:
        raise AppException(
            "Invalid authentication token.",
            status_code=401,
            code="invalid_token",
        ) from None

    user = get_user_by_username(db, username)
    if user is None:
        raise AppException(
            "Authenticated user was not found.",
            status_code=401,
            code="user_not_found",
        )

    if not user.is_active:
        raise AppException(
            "User is inactive.",
            status_code=403,
            code="inactive_user",
        )

    return user


def get_current_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_superuser:
        raise AppException(
            "Administrative access is required.",
            status_code=403,
            code="admin_required",
        )
    return user


current_user = Annotated[User, Depends(get_current_user)]
current_admin_user = Annotated[User, Depends(get_current_admin_user)]

CurrentUser = current_user
CurrentAdminUser = current_admin_user
