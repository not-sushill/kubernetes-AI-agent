"""
Parsing helpers for kubectl output.
"""

from __future__ import annotations

import json
from typing import Any

from app.kubernetes.exceptions import KubectlOutputParseError
from app.kubernetes.models import CommandResult


def parse_json_output(result: CommandResult) -> dict[str, Any]:
    """
    Parse kubectl JSON output into a dictionary.
    """

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise KubectlOutputParseError(
            message="kubectl returned invalid JSON output.",
            command=result.command,
        ) from exc

    if not isinstance(payload, dict):
        raise KubectlOutputParseError(
            message="kubectl JSON output was not an object.",
            command=result.command,
        )

    return payload
