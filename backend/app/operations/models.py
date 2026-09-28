from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base_model import BaseModel

class OperationRecord(BaseModel):
    __tablename__ = 'operations'
    kind: Mapped[str] = mapped_column(String(40), index=True)
    state: Mapped[str] = mapped_column(String(40), default='SAVED', index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
