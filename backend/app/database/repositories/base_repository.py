from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository for all database repositories.
    """

    def __init__(self, db: Session):
        self.db = db
