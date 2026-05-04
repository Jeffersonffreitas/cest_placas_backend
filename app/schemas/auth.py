from pydantic import BaseModel

from app.schemas.user import UserRead


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthenticatedUserResponse(BaseModel):
    user: UserRead
