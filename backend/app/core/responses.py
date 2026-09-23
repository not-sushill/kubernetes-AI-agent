from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class ApiResponse(GenericModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: str
    details: Any | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )