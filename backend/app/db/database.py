from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.database.base import Base

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL, pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
