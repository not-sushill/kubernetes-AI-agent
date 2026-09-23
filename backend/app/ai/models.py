from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AISeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AIRootCause(BaseModel):
    title: str
    explanation: str
    severity: AISeverity
    confidence: int = Field(default=0.0, ge=0.0, le=100.0)
    evidence: list[str] = Field(default_factory=list)


class AIRecommendation(BaseModel):
    action: str
    reason: str
    risk: str
    commands: list[str] = Field(default_factory=list)


class AIDiagnosis(BaseModel):
    summary: str
    severity: AISeverity
    confidence: int = Field(default=0.0, ge=0.0, le=100.0)
    root_causes: list[AIRootCause] = Field(default_factory=list)
    recommendations: list[AIRecommendation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)