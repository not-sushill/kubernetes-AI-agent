from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base_model import BaseModel as Record

class FixProposal(Record):
    __tablename__ = 'fix_proposals'
    investigation_id: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(40), default='PROPOSED')
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

class ProposeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    deployment: str = Field(min_length=1, max_length=253)
    objective: str = Field(min_length=10, max_length=2000)
    assessment_only: bool = False
    source_proposal_id: str | None = Field(default=None, max_length=100)

class Approval(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirmation: str = Field(max_length=1000)

class Change(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(max_length=300)
    value: Any

class Hypothesis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    explanation: str = Field(min_length=5,max_length=500)
    evidence_ids: list[int] = Field(max_length=5)
    confidence: Literal['low','medium','high']
    uncertainty: str = Field(min_length=5,max_length=400)
    check_id: Literal['deployment_status','pod_status','warning_events','manual_check']

class ModelPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['propose', 'needs_information']
    explanation: str = Field(min_length=10, max_length=3000)
    evidence_ids: list[int] = Field(max_length=10)
    checks: list[str] = Field(max_length=10)
    changes: list[Change] = Field(max_length=8)
    hypotheses: list[Hypothesis] = Field(default_factory=list,max_length=3)

class DiagnosticRun(Record):
    __tablename__ = 'diagnostic_runs'
    proposal_id: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

class RunCheck(BaseModel):
    model_config = ConfigDict(extra='forbid')
    check_id: Literal['deployment_status','pod_status','warning_events']
