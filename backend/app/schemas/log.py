from pydantic import BaseModel


class PodLogsResponse(BaseModel):
    pod: str
    namespace: str
    line_count: int
    logs: list[str]
