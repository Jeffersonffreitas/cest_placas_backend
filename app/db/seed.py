from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.auth import ensure_default_admin


def seed_admin_user() -> None:
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    seed_admin_user()
    print("Default admin user is ready.")


if __name__ == "__main__":
    main()
