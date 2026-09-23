from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.kubernetes.exceptions import (
    CommandExecutionError,
    InvalidKubectlArgumentError,
    KubectlNotFoundError,
    KubectlOutputParseError,
    KubectlTimeoutError,
)


def _error_response(
    status_code: int,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "error": error,
        "message": message,
    }

    if details:
        payload["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register Kubernetes API exception handlers."""

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return _error_response(503, "investigation_storage_unavailable", "Local investigation storage is unavailable. Check backend logs and database configuration.")

    @app.exception_handler(InvalidKubectlArgumentError)
    async def invalid_kubectl_argument_handler(
        _request: Request,
        exc: InvalidKubectlArgumentError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="invalid_kubectl_argument",
            message=str(exc),
        )

    @app.exception_handler(KubectlNotFoundError)
    async def kubectl_not_found_handler(
        _request: Request,
        exc: KubectlNotFoundError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="kubectl_not_found",
            message=str(exc),
        )

    @app.exception_handler(KubectlTimeoutError)
    async def kubectl_timeout_handler(
        _request: Request,
        exc: KubectlTimeoutError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error="kubectl_timeout",
            message=str(exc),
        )

    @app.exception_handler(CommandExecutionError)
    async def command_execution_handler(
        _request: Request,
        exc: CommandExecutionError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error="kubectl_command_failed",
            message=str(exc),
            details={
                "command": exc.command,
                "stderr": exc.stderr,
                "return_code": exc.return_code,
            },
        )

    @app.exception_handler(KubectlOutputParseError)
    async def kubectl_parse_handler(
        _request: Request,
        exc: KubectlOutputParseError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error="kubectl_output_parse_error",
            message=str(exc),
            details={
                "command": exc.command,
            },
        )
