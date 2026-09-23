from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.investigations.models import InvestigationCreate
from app.investigations.service import InvestigationService


router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)


def get_investigation_service(
    db: Session = Depends(get_db),
) -> InvestigationService:
    return InvestigationService(db=db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    payload: InvestigationCreate,
    service: InvestigationService = Depends(
        get_investigation_service,
    ),
):
    try:
        result = service.create(payload)

        return result.model_dump(
            mode="json",
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/{investigation_id}",
)
def get_investigation(
    investigation_id: str,
    service: InvestigationService = Depends(
        get_investigation_service,
    ),
):
    try:
        result = service.get(
            investigation_id,
        )

        return result.model_dump(
            mode="json",
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc