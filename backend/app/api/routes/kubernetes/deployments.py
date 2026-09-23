from __future__ import annotations
import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from app.kubernetes.exceptions import CommandExecutionError, KubectlTimeoutError

from app.kubernetes.services.deployment_yaml_service import (
    DeploymentYamlService,
)

from app.kubernetes.services.deployment_service import DeploymentService
from app.schemas.deployment import (
    DeploymentDetailResponse,
    DeploymentEventsResponse,
    DeploymentResponse,
    DeploymentYamlResponse,
    DeploymentApplyResponse,
    DeploymentBackupDetailResponse,
    DeploymentBackupResponse,
    DeploymentRestoreResponse,
    DeploymentYamlRequest,
    DeploymentApplyRequest,
    DeploymentRestoreRequest,
    DeploymentYamlValidationResponse,
)

router = APIRouter(prefix="/deployments", tags=["Deployments"])
logger = logging.getLogger(__name__)

def get_deployment_service() -> DeploymentService:
    return DeploymentService()


@router.get(
    "",
    response_model=list[DeploymentResponse],
)
def list_all_deployments(
    service: DeploymentService = Depends(get_deployment_service),
) -> list[dict[str, Any]]:
    return service.list_deployments()


@router.get(
    "/{namespace}",
    response_model=list[DeploymentResponse],
)
def list_namespace_deployments(
    namespace: str,
    service: DeploymentService = Depends(get_deployment_service),
) -> list[dict[str, Any]]:
    return service.list_deployments(namespace)


@router.get(
    "/{namespace}/{deployment}",
    response_model=DeploymentDetailResponse,
)
def get_deployment(
    namespace: str,
    deployment: str,
    service: DeploymentService = Depends(get_deployment_service),
) -> dict[str, Any]:
    return service.get_deployment(namespace, deployment)


@router.get(
    "/{namespace}/{deployment}/events",
    response_model=DeploymentEventsResponse,
    summary="Get Deployment Events",
)
def get_deployment_events(
    namespace: str,
    deployment: str,
    service: DeploymentService = Depends(get_deployment_service),
) -> dict[str, Any]:
    return service.get_events(namespace, deployment)


@router.get(
    "/{namespace}/{deployment}/yaml",
    response_model=DeploymentYamlResponse,
    summary="Get Deployment YAML",
)
def get_deployment_yaml(
    namespace: str,
    deployment: str,
    service: DeploymentService = Depends(get_deployment_service),
) -> dict[str, str]:
    return service.get_yaml(namespace, deployment)
def get_deployment_yaml_service() -> DeploymentYamlService:
    return DeploymentYamlService()

@router.post(
    "/{namespace}/{deployment}/yaml/validate",
    response_model=DeploymentYamlValidationResponse,
)
def validate_deployment_yaml(
    namespace: str,
    deployment: str,
    request: DeploymentYamlRequest,
    service: DeploymentYamlService = Depends(
        get_deployment_yaml_service
    ),
):
    try:
        return service.validate(
            namespace,
            deployment,
            request.yaml,
        )

    except KubectlTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except CommandExecutionError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{str(exc)}\n\n"
                f"Command: {exc.command}\n"
                f"Exit code: {exc.return_code}\n"
                f"Error: {exc.stderr.strip() or 'No stderr returned'}"
            ),
        ) from exc

    except Exception as exc:
        logger.exception("Deployment YAML operation failed for %s/%s", namespace, deployment)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(exc)}",
        ) from exc

@router.post(
    "/{namespace}/{deployment}/yaml/apply",
    response_model=DeploymentApplyResponse,
)
def apply_deployment_yaml(
    namespace: str,
    deployment: str,
    request: DeploymentApplyRequest,
    service: DeploymentYamlService = Depends(
        get_deployment_yaml_service
    ),
):
    if request.confirmation != f"APPLY {namespace}/{deployment}":
        raise HTTPException(status_code=400, detail="Typed confirmation does not match the deployment.")
    try:
        return service.apply(
            namespace,
            deployment,
            request.yaml,
        )

    except KubectlTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except CommandExecutionError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{str(exc)}\n\n"
                f"Command: {exc.command}\n"
                f"Exit code: {exc.return_code}\n"
                f"Error: {exc.stderr.strip() or 'No stderr returned'}"
            ),
        ) from exc

    except Exception as exc:
        logger.exception("Deployment YAML operation failed for %s/%s", namespace, deployment)
        raise HTTPException(
            status_code=500,
            detail=f"Apply failed: {str(exc)}",
        ) from exc

@router.get(
    "/{namespace}/{deployment}/backups",
    response_model=list[DeploymentBackupResponse],
)
def list_deployment_backups(
    namespace: str,
    deployment: str,
    service: DeploymentYamlService = Depends(
        get_deployment_yaml_service
    ),
):
    return service.list_backups(
        namespace,
        deployment,
    )


@router.get(
    "/{namespace}/{deployment}/backups/{backup_id}",
    response_model=DeploymentBackupDetailResponse,
)
def get_deployment_backup(
    namespace: str,
    deployment: str,
    backup_id: str,
    service: DeploymentYamlService = Depends(
        get_deployment_yaml_service
    ),
):
    try:
        return service.get_backup(
            namespace,
            deployment,
            backup_id,
        )
    except KubectlTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post(
    "/{namespace}/{deployment}/backups/{backup_id}/restore",
    response_model=DeploymentRestoreResponse,
)
def restore_deployment_backup(
    namespace: str,
    deployment: str,
    backup_id: str,
    request: DeploymentRestoreRequest,
    service: DeploymentYamlService = Depends(
        get_deployment_yaml_service
    ),
):
    if request.confirmation != f"RESTORE {namespace}/{deployment} {backup_id}":
        raise HTTPException(status_code=400, detail="Typed confirmation does not match the deployment and backup.")
    try:
        return service.restore(
            namespace,
            deployment,
            backup_id,
        )
    except KubectlTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc