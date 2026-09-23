from datetime import datetime

from pydantic import BaseModel


class InvestigationResponse(BaseModel):
    id: int
    cluster: str
    namespace: str
    resource_type: str
    resource_name: str
    status: str
    request_id: str | None
    result: dict
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }