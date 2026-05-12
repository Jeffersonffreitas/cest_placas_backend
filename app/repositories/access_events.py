from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent


def create_access_event(db: Session, data: dict[str, object]) -> AccessEvent:
    access_event = AccessEvent(**data)
    db.add(access_event)
    return access_event
