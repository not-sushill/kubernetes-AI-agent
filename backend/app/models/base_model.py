from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.base import Base


class BaseModel(Base):
    """
    Base model inherited by every database table.
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
