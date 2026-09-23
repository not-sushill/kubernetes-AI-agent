from __future__ import annotations

from typing import Any

from app.ai.service import AIService
from app.kubernetes.services.investigation.diagnostics.workload_diagnostics import WorkloadDiagnosticsService
from app.kubernetes.services.investigation.correlation.pod_root_cause import (
    PodRootCauseService,
)
from app.kubernetes.services.investigation.diagnostics.pod_diagnostics import (
    PodDiagnosticsService,
)


class InvestigationAnalysisService:
    """
    Runs deterministic Kubernetes diagnostics and root-cause correlation,
    followed by optional local AI diagnosis through Ollama.
    """

    def __init__(self) -> None:
        self.diagnostics_service = PodDiagnosticsService()
        self.root_cause_service = PodRootCauseService()
        self.ai_service = AIService()

    def analyze(
        self,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        # ---------------------------------------------------------------
        # 1. Deterministic diagnostics
        # ---------------------------------------------------------------
        diagnostics = self.diagnostics_service.analyze(
            evidence,
        )

        diagnostics["issues"].extend(WorkloadDiagnosticsService().analyze(evidence))
        diagnostics["issue_count"] = len(diagnostics["issues"])

        normalized_diagnostics = self._normalize_diagnostics(
            diagnostics,
        )

        # ---------------------------------------------------------------
        # 2. Deterministic root-cause correlation
        # ---------------------------------------------------------------
        root_cause_result = self.root_cause_service.analyze(
            investigation=evidence,
            diagnostics=diagnostics,
        )

        normalized_root_causes = self._normalize_root_causes(
            root_cause_result,
        )

        # ---------------------------------------------------------------
        # 3. Optional AI diagnosis
        # ---------------------------------------------------------------
        ai_diagnosis = self.ai_service.diagnose(
            evidence=evidence,
            diagnostics=normalized_diagnostics,
            root_causes=normalized_root_causes,
        )

        limitations = list(evidence.get("limitations") or [])
        for name, value in evidence.items():
            if isinstance(value, dict) and value.get("status") == "failed":
                limitations.append(f"{name} evidence unavailable: {value.get('error')}")
        if ai_diagnosis is not None:
            ai_diagnosis = ai_diagnosis.model_copy(update={"limitations": list(dict.fromkeys([*ai_diagnosis.limitations, *limitations]))})

        return {
            "diagnostics": normalized_diagnostics,
            "root_causes": normalized_root_causes,
            "ai": (
                ai_diagnosis.model_dump(mode="json")
                if ai_diagnosis is not None
                else None
            ),
        }

    @staticmethod
    def _normalize_diagnostics(
        diagnostics: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues = diagnostics.get("issues") or []

        if not isinstance(issues, list):
            return []

        return [
            issue
            for issue in issues
            if isinstance(issue, dict)
        ]

    @staticmethod
    def _normalize_root_causes(
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        root_causes = result.get("root_causes") or []

        if not isinstance(root_causes, list):
            return []

        return [
            root_cause
            for root_cause in root_causes
            if isinstance(root_cause, dict)
        ]