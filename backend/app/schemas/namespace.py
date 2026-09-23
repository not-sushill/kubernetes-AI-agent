from pydantic import BaseModel


class NamespaceResponse(BaseModel):
    name: str
    status: str
    age: str
