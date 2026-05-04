from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.scalars(statement).first()


def create_user(
    db: Session,
    *,
    username: str,
    password_hash: str,
    full_name: str | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        full_name=full_name,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
