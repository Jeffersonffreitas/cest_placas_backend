from sqlalchemy.orm import Session

from app.models.plate_read import PlateRead


def create_plate_read(db: Session, data: dict[str, object]) -> PlateRead:
    plate_read = PlateRead(**data)
    db.add(plate_read)
    return plate_read
