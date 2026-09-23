from pydantic import BaseModel, Field


class NodeSummary(BaseModel):

    name: str

    status: str

    roles: str

    version: str

    internal_ip: str

    os_image: str

    kernel_version: str

    container_runtime: str

    age: str


class NodeCondition(BaseModel):

    type: str

    status: str

    reason: str

    message: str


class NodeDetail(NodeSummary):

    labels: dict

    annotations: dict

    capacity: dict

    allocatable: dict

    conditions: list[NodeCondition]
    provider_id: str = ""
    pod_cidr: str = ""
    unschedulable: bool = False
    metrics: dict = Field(default_factory=lambda: {"available": False, "cpu": None, "memory": None})
    health_score: int | None = None
    yaml: str = ""
    events: list[dict] = Field(default_factory=list)
