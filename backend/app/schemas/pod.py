from pydantic import BaseModel


class PodResponse(BaseModel):
    namespace: str
    name: str
    status: str
    ready: str
    restarts: int
    node: str
    pod_ip: str
    age: str


class ContainerResponse(BaseModel):
    name: str
    image: str
    ready: bool
    restart_count: int


class PodDetailResponse(BaseModel):
    namespace: str
    name: str
    status: str
    node: str
    pod_ip: str
    host_ip: str
    qos_class: str
    service_account: str
    labels: dict[str, str]
    annotations: dict[str, str]
    containers: list[ContainerResponse]
