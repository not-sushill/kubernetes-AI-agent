"""Compatibility exports without eagerly creating a circular database import."""
from app.database.base import Base

__all__ = ["Base", "engine", "SessionLocal"]


def __getattr__(name):
    if name in ("engine", "SessionLocal"):
        from app.db import database
        return getattr(database, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
