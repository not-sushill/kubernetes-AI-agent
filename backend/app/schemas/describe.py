from pydantic import BaseModel


class PodDescribeResponse(BaseModel):
    pod: str
    namespace: str
    description: str
