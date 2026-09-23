from __future__ import annotations

from fastapi import HTTPException

from app.core.audit_logger import AuditLogger
from app.core.read_only import ReadOnlyMode


class OperationsGuard:

    @staticmethod
    def check(
        operation: str,
        resource: str,
        name: str,
    ) -> None:

        try:

            ReadOnlyMode.ensure_write_allowed()

        except PermissionError as exc:

            AuditLogger.write(
                action=operation,
                resource=resource,
                name=name,
                status="BLOCKED",
                message=str(exc),
            )

            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc