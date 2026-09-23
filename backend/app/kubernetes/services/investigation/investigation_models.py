# backend/app/kubernetes/services/investigation/investigation_models.py

from __future__ import annotations

from typing import Any


def create_investigation(
    namespace: str,
    pod: str,
    pod_data: dict[str, Any],
    events: list[dict[str, Any]],
    current_logs: dict[str, str],
    previous_logs: dict[str, str],
    issues: list[dict[str, Any]],
    root_causes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "pod": pod,
        "pod_data": pod_data,

        "events": events,

        "logs": {
            "current": current_logs,
            "previous": previous_logs,
        },

        "diagnostics": {
            "issue_count": len(issues),
            "issues": issues,
        },

        "root_cause_count": len(
            root_causes
        ),

        "root_causes": root_causes,
    }