# ============================================================
# backend/app/investigations/models.py
# ============================================================

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator
from app.kubernetes.validators import validate_namespace, validate_object_name

from app.ai.models import AIDiagnosis


# ============================================================
# RESOURCE / STATUS ENUMS
# ============================================================

class InvestigationResourceType(StrEnum):
    NAMESPACE = "namespace"
    POD = "pod"
    DEPLOYMENT = "deployment"
    SERVICE = "service"


class InvestigationStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class InvestigationSectionStatus(StrEnum):
    COLLECTED = "collected"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================
# TARGET
# ============================================================

class InvestigationTarget(BaseModel):
    namespace: str
    resource_type: InvestigationResourceType
    resource_name: str


# ============================================================
# CREATE REQUEST
# ============================================================

class InvestigationCreate(BaseModel):
    namespace: str

    resource_type: InvestigationResourceType = (
        InvestigationResourceType.NAMESPACE
    )

    resource_name: str | None = None

    log_tail: int = Field(
        default=200,
        ge=0,
        le=5000,
    )

    include_previous_logs: bool = False

    @field_validator("namespace")
    @classmethod
    def valid_namespace(cls, value: str) -> str:
        try:
            return validate_namespace(value)
        except Exception as exc:
            raise ValueError(str(exc)) from exc

    @model_validator(mode="after")
    def valid_target(self):
        if self.resource_type != InvestigationResourceType.NAMESPACE:
            if not self.resource_name or not self.resource_name.strip():
                raise ValueError("resource_name is required for pod, deployment and service investigations")
        if self.resource_name:
            try:
                self.resource_name = validate_object_name(self.resource_name)
            except Exception as exc:
                raise ValueError(str(exc)) from exc
        return self

    def target(self) -> InvestigationTarget:
        resource_name = (
            self.resource_name.strip()
            if self.resource_name
            else self.namespace
        )

        return InvestigationTarget(
            namespace=self.namespace,
            resource_type=self.resource_type,
            resource_name=resource_name,
        )


# ============================================================
# EVIDENCE SECTION
# ============================================================

class InvestigationSection(BaseModel):
    status: InvestigationSectionStatus
    data: object | None = None
    error: str | None = None

    @classmethod
    def collected(
        cls,
        data: object,
    ) -> "InvestigationSection":
        return cls(
            status=InvestigationSectionStatus.COLLECTED,
            data=data,
            error=None,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> "InvestigationSection":
        return cls(
            status=InvestigationSectionStatus.FAILED,
            data=None,
            error=error,
        )

    @classmethod
    def skipped(
        cls,
        error: str,
    ) -> "InvestigationSection":
        return cls(
            status=InvestigationSectionStatus.SKIPPED,
            data=None,
            error=error,
        )


# ============================================================
# INVESTIGATION EVIDENCE
# ============================================================

class InvestigationEvidence(BaseModel):
    namespace: InvestigationSection
    pod: InvestigationSection
    deployment: InvestigationSection
    replicaset: InvestigationSection
    node: InvestigationSection
    events: InvestigationSection
    logs: InvestigationSection
    services: InvestigationSection
    pvc: InvestigationSection
    metrics: InvestigationSection

    endpoints: InvestigationSection = Field(default_factory=lambda: InvestigationSection.skipped("Not collected."))
    network_policies: InvestigationSection = Field(default_factory=lambda: InvestigationSection.skipped("Not collected."))
    resource_quotas: InvestigationSection = Field(default_factory=lambda: InvestigationSection.skipped("Not collected."))
    limitations: list[str] = Field(default_factory=list)

    def run_status(self) -> InvestigationStatus:
        sections = [
            self.namespace,
            self.pod,
            self.deployment,
            self.replicaset,
            self.node,
            self.events,
            self.logs,
            self.services,
            self.pvc,
            self.metrics,
            self.endpoints,
            self.network_policies,
            self.resource_quotas,
        ]

        failed_count = sum(
            section.status
            == InvestigationSectionStatus.FAILED
            for section in sections
        )

        collected_count = sum(
            section.status
            == InvestigationSectionStatus.COLLECTED
            for section in sections
        )

        if failed_count and collected_count == 0:
            return InvestigationStatus.FAILED

        if failed_count > 0 or self.limitations:
            return InvestigationStatus.PARTIAL

        if collected_count == 0:
            return InvestigationStatus.PARTIAL

        return InvestigationStatus.COMPLETED


# ============================================================
# AI / ANALYSIS
# ============================================================

class InvestigationAnalysis(BaseModel):
    diagnostics: list[dict] = Field(
        default_factory=list
    )

    root_causes: list[dict] = Field(
        default_factory=list
    )

    ai: AIDiagnosis | None = None


# ============================================================
# INVESTIGATION RESPONSE
# ============================================================

class Investigation(BaseModel):
    id: str
    target: InvestigationTarget
    status: InvestigationStatus
    evidence: InvestigationEvidence
    analysis: InvestigationAnalysis = Field(
        default_factory=InvestigationAnalysis
    )
    created_at: datetime
    updated_at: datetime


# ============================================================
# INVESTIGATION LIST
# ============================================================

class InvestigationListItem(BaseModel):
    id: str
    cluster: str
    namespace: str
    resource_type: InvestigationResourceType
    resource_name: str
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime


class InvestigationListResponse(BaseModel):
    items: list[InvestigationListItem]
    total: int
    page: int
    page_size: int
    pages: int