from pydantic import BaseModel


class PodLogsResponse(BaseModel):
    pod: str
    namespace: str
    line_count: int
    logs: list[str]

    container: str | None = None
    previous: bool = False
    available: bool = True
    message: str | None = None
