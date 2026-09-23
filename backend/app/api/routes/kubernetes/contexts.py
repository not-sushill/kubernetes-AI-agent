from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.kubernetes.client import KubectlClient


router = APIRouter(
    prefix="/contexts",
    tags=["Kubernetes"],
)


class ContextSwitchRequest(BaseModel):
    context: str = Field(
        min_length=1,
        max_length=255,
    )


@router.get(
    "",
)
def list_contexts():
    """
    Return all configured Kubernetes contexts
    and the currently active context.
    """

    client = KubectlClient()

    contexts_result = client.list_contexts()

    if contexts_result.return_code != 0:
        raise HTTPException(
            status_code=500,
            detail=contexts_result.stderr
            or "Failed to list Kubernetes contexts.",
        )

    current_result = client.current_context()

    if current_result.return_code != 0:
        raise HTTPException(
            status_code=500,
            detail=current_result.stderr
            or "Failed to get current Kubernetes context.",
        )

    contexts = [
        line.strip()
        for line in contexts_result.stdout.splitlines()
        if line.strip()
    ]

    current_context = current_result.stdout.strip()

    return {
        "contexts": contexts,
        "current_context": current_context,
    }


@router.post(
    "/select",
)
def select_context(
    payload: ContextSwitchRequest,
):
    """
    Switch the active Kubernetes context.
    """

    client = KubectlClient()

    context_name = payload.context.strip()

    if not context_name:
        raise HTTPException(
            status_code=400,
            detail="Context name cannot be empty.",
        )

    contexts_result = client.list_contexts()

    if contexts_result.return_code != 0:
        raise HTTPException(
            status_code=500,
            detail=contexts_result.stderr
            or "Failed to list Kubernetes contexts.",
        )

    available_contexts = {
        line.strip()
        for line in contexts_result.stdout.splitlines()
        if line.strip()
    }

    if context_name not in available_contexts:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Kubernetes context "
                f"'{context_name}' was not found."
            ),
        )

    result = client.switch_context(
        context_name,
    )

    if result.return_code != 0:
        raise HTTPException(
            status_code=500,
            detail=result.stderr
            or "Failed to switch Kubernetes context.",
        )

    current_result = client.current_context()

    if current_result.return_code != 0:
        raise HTTPException(
            status_code=500,
            detail=current_result.stderr
            or "Context was switched but failed to verify it.",
        )

    return {
        "success": True,
        "message": "Kubernetes context switched successfully.",
        "current_context": current_result.stdout.strip(),
    }