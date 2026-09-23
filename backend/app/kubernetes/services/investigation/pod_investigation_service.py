# backend/app/kubernetes/services/investigation/pod_investigation_service.py

from __future__ import annotations

from typing import Any

from app.kubernetes.services.pod_service import PodService

from app.kubernetes.services.investigation.diagnostics import (
    PodDiagnosticsService,
)

from app.kubernetes.services.investigation.correlation import (
    PodRootCauseService,
)

from .investigation_models import create_investigation


class PodInvestigationService:
    """
    Complete deterministic pod investigation pipeline.
    """

    def __init__(
        self,
        pod_service: PodService | None = None,
        diagnostics: PodDiagnosticsService | None = None,
        root_cause_service: PodRootCauseService | None = None,
    ) -> None:
        self.pod_service = (
            pod_service
            or PodService()
        )

        self.diagnostics = (
            diagnostics
            or PodDiagnosticsService()
        )

        self.root_cause_service = (
            root_cause_service
            or PodRootCauseService()
        )

    def investigate(
        self,
        namespace: str,
        pod: str,
        tail: int = 200,
    ) -> dict[str, Any]:

        pod_detail = self.pod_service.get_pod(
            namespace,
            pod,
        )

        events_result = self.pod_service.get_events(
            namespace,
            pod,
        )

        events = (
            events_result.get("events")
            or []
        )

        current_logs = self._collect_logs(
            namespace=namespace,
            pod=pod,
            pod_detail=pod_detail,
            previous=False,
            tail=tail,
        )

        previous_logs = self._collect_logs(
            namespace=namespace,
            pod=pod,
            pod_detail=pod_detail,
            previous=True,
            tail=tail,
        )

        investigation = {
            "pod": pod_detail,
            "events": {
                "pod": pod,
                "namespace": namespace,
                "total_events": len(events),
                "events": events,
            },
            "logs": {
                "current": current_logs,
                "previous": previous_logs,
            },
        }

        diagnostics = self.diagnostics.analyze(
            investigation
        )

        root_cause_analysis = (
            self.root_cause_service.analyze(
                investigation=investigation,
                diagnostics=diagnostics,
            )
        )

        return create_investigation(
            namespace=namespace,
            pod=pod,
            pod_data=pod_detail,
            events=events,
            current_logs=current_logs,
            previous_logs=previous_logs,
            issues=(
                diagnostics.get(
                    "issues",
                    [],
                )
            ),
            root_causes=(
                root_cause_analysis.get(
                    "root_causes",
                    [],
                )
            ),
        )

    def _collect_logs(
        self,
        namespace: str,
        pod: str,
        pod_detail: dict[str, Any],
        previous: bool,
        tail: int,
    ) -> dict[str, str]:

        collected: dict[str, str] = {}

        containers = (
            pod_detail.get("containers")
            or []
        )

        for container in containers:
            container_name = container.get(
                "name"
            )

            if not container_name:
                continue

            try:
                result = self.pod_service.get_logs(
                    namespace=namespace,
                    pod=pod,
                    container=container_name,
                    previous=previous,
                    tail=tail,
                    timestamps=True,
                )

                lines = (
                    result.get("logs")
                    or []
                )

                if isinstance(
                    lines,
                    list,
                ):
                    collected[
                        container_name
                    ] = "\n".join(
                        str(line)
                        for line in lines
                    )
                else:
                    collected[
                        container_name
                    ] = str(lines)

            except Exception as exc:
                if previous:
                    collected[
                        container_name
                    ] = ""
                else:
                    collected[
                        container_name
                    ] = (
                        "[Log unavailable: "
                        f"{exc}]"
                    )

        return collected