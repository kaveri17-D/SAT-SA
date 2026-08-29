from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
from app.core.logging import logger

db_url = settings.active_database_url

# Configure connect_args for SQLite dev environment vs Postgres
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from app.models.base import Base


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
