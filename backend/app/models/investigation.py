from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.models.base_model import BaseModel


class Investigation(BaseModel):
    """
    Stores every Kubernetes investigation.
    """

    __tablename__ = "investigations"

    cluster: Mapped[str] = mapped_column(String(200))

    namespace: Mapped[str] = mapped_column(String(200))

    resource_type: Mapped[str] = mapped_column(String(100))

    resource_name: Mapped[str] = mapped_column(String(300))

    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
    )

    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
