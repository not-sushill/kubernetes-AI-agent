"""
Shared models for Kubernetes operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    """
    Result of a kubectl command execution.
    """

    command: str
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClusterInfo(BaseModel):
    """
    Kubernetes cluster information.
    """

    connected: bool
    context: str | None = None
    cluster: str | None = None
    server_version: str | None = None
    kubectl_version: str | None = None


class NamespaceInfo(BaseModel):
    """
    Kubernetes namespace information.
    """

    name: str
    status: str
    age: str | None = None


class PodInfo(BaseModel):
    """
    Kubernetes pod information.
    """

    name: str
    namespace: str
    ready: str
    status: str
    restarts: int
    age: str


class EventInfo(BaseModel):
    """
    Kubernetes event information.
    """

    namespace: str
    type: str
    reason: str
    involved_object: str
    message: str
    timestamp: str


class InvestigationEvidence(BaseModel):
    """
    Complete evidence collected during an investigation.
    """

    cluster: ClusterInfo | None = None

    namespaces: list[NamespaceInfo] = Field(default_factory=list)

    pods: list[PodInfo] = Field(default_factory=list)

    events: list[EventInfo] = Field(default_factory=list)

    raw_outputs: dict[str, Any] = Field(default_factory=dict)
