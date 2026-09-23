from pydantic import BaseModel


class EventResponse(BaseModel):
    type: str
    reason: str
    message: str
    count: int
    first_timestamp: str
    last_timestamp: str


class PodEventsResponse(BaseModel):
    pod: str
    namespace: str
    total_events: int
    events: list[EventResponse]
