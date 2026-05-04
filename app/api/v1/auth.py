from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.security import create_access_token
from app.db.deps import get_db
from app.schemas.auth import AuthenticatedUserResponse, TokenResponse
from app.schemas.user import UserRead
from app.services.auth import authenticate_user


router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate administrative user",
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(
        db,
        username=form_data.username,
        password=form_data.password,
    )
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return TokenResponse(
        access_token=create_access_token(str(user.username), expires_delta=expires_delta),
        expires_in=int(expires_delta.total_seconds()),
    )


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user",
)
def read_current_user(user: CurrentUser) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse(user=UserRead.model_validate(user))
