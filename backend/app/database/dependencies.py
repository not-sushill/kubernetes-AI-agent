from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI database dependency.

    Creates a database session and guarantees
    that it is closed after the request.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
