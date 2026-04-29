from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=settings.mysql_pool_pre_ping,
    pool_recycle=settings.mysql_pool_recycle,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

