from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import app_logger

AUDIT_DIR = (
    Path(__file__).resolve().parents[2]
    / "audit"
)

AUDIT_DIR.mkdir(
    exist_ok=True,
)


class AuditLogger:

    @staticmethod
    def write(
        action: str,
        resource: str,
        name: str,
        status: str,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:

        now = datetime.utcnow()

        logfile = (
            AUDIT_DIR
            / f"{now:%Y-%m-%d}.log"
        )

        payload = {
            "timestamp": now.isoformat(),
            "action": action,
            "resource": resource,
            "name": name,
            "status": status,
            "message": message,
            "metadata": metadata or {},
        }

        with logfile.open(
            "a",
            encoding="utf-8",
        ) as f:

            f.write(
                json.dumps(payload)
            )

            f.write("\n")

        app_logger.info(
            "AUDIT {} {} {}",
            action,
            resource,
            name,
        )