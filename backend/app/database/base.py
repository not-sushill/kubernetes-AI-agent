from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Root SQLAlchemy Declarative Base.
    """

    pass


# Import every model here.
# This ensures Alembic discovers metadata.
import app.models  # noqa: E402,F401
