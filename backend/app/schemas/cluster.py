from pydantic import BaseModel


class ClusterHealthResponse(BaseModel):
    connected: bool
    current_context: str
    kubectl_version: str
    server_version: str
    latency_ms: float
