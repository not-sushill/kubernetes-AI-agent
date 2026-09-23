# ============================================================
# 6. backend/app/investigations/router.py
# ============================================================

from collections.abc import Generator

from fastapi import APIRouter, Depends, Query, status

from app.db.database import SessionLocal

from app.investigations.models import (
    Investigation,
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationResourceType,
    InvestigationStatus,
)

from app.investigations.service import InvestigationService


router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)


def get_investigation_service() -> Generator[
    InvestigationService,
    None,
    None,
]:
    db = SessionLocal()

    try:
        yield InvestigationService(db=db)
    finally:
        db.close()


@router.post(
    "",
    response_model=Investigation,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    request: InvestigationCreate,
    service: InvestigationService = Depends(
        get_investigation_service
    ),
) -> Investigation:
    return service.create(request)


@router.get(
    "",
    response_model=InvestigationListResponse,
)
def list_investigations(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
    namespace: str | None = Query(
        default=None,
        max_length=253,
    ),
    investigation_status: InvestigationStatus | None = Query(
        default=None,
        alias="status",
    ),
    resource_type: InvestigationResourceType | None = Query(
        default=None,
    ),
    service: InvestigationService = Depends(
        get_investigation_service
    ),
) -> InvestigationListResponse:
    return service.list(
        page=page,
        page_size=page_size,
        search=search,
        namespace=namespace,
        investigation_status=investigation_status,
        resource_type=resource_type,
    )


@router.get(
    "/{investigation_id}",
    response_model=Investigation,
)
def get_investigation(
    investigation_id: str,
    service: InvestigationService = Depends(
        get_investigation_service
    ),
) -> Investigation:
    return service.get(investigation_id)