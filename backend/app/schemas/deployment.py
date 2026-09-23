from pydantic import BaseModel

from app.schemas.event import EventResponse
from app.kubernetes.exceptions import CommandExecutionError

class DeploymentResponse(BaseModel):
    namespace: str
    name: str
    replicas: int
    ready_replicas: int
    available_replicas: int
    updated_replicas: int
    strategy: str
    age: str


class DeploymentContainerResponse(BaseModel):
    name: str
    image: str


class DeploymentConditionResponse(BaseModel):
    type: str
    status: str
    reason: str
    message: str
    last_transition_time: str


class DeploymentDetailResponse(DeploymentResponse):
    selector: dict[str, str]
    labels: dict[str, str]
    annotations: dict[str, str]
    containers: list[DeploymentContainerResponse]
    conditions: list[DeploymentConditionResponse]


class DeploymentEventsResponse(BaseModel):
    deployment: str
    namespace: str
    total_events: int
    events: list[EventResponse]


class DeploymentYamlResponse(BaseModel):
    deployment: str
    namespace: str
    yaml: str

class DeploymentYamlRequest(BaseModel):
    yaml: str


class DeploymentYamlValidationResponse(BaseModel):
    valid: bool
    formatted_yaml: str
    message: str


class DeploymentApplyResponse(BaseModel):
    success: bool
    applied: bool = False
    rollout_status: str = "unknown"
    message: str = ""
    deployment: str
    namespace: str
    backup_id: str
    apply_output: str
    rollout_output: str


class DeploymentBackupResponse(BaseModel):
    id: str
    context: str
    namespace: str
    deployment: str
    created_at: str
    reason: str


class DeploymentBackupDetailResponse(BaseModel):
    metadata: DeploymentBackupResponse
    yaml: str


class DeploymentRestoreResponse(BaseModel):
    success: bool
    applied: bool = False
    rollout_status: str = "unknown"
    message: str = ""
    deployment: str
    namespace: str
    restored_backup_id: str
    recovery_backup_id: str
    apply_output: str
    rollout_output: str

class DeploymentApplyRequest(DeploymentYamlRequest):
    confirmation: str


class DeploymentRestoreRequest(BaseModel):
    confirmation: str
