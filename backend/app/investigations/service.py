# ============================================================
# backend/app/investigations/service.py
# REPLACE THE ENTIRE FILE
# ============================================================

from __future__ import annotations

from math import ceil

from fastapi import HTTPException
from sqlalchemy import or_

from app.investigations.analysis import (
    InvestigationAnalysisService,
)

from app.investigations.models import (
    Investigation,
    InvestigationCreate,
    InvestigationEvidence,
    InvestigationListItem,
    InvestigationListResponse,
)
from app.investigations.collector import InvestigationCollector
from app.models.investigation import (
    Investigation as InvestigationRecord,
)


class InvestigationService:
    def __init__(
        self,
        db,
        collector=None,
        cluster_service=None,
    ) -> None:
        self.db = db

        self.collector = collector or InvestigationCollector()

        self.cluster_service = cluster_service

        self.analysis_service = (
            InvestigationAnalysisService()
        )

    # ========================================================
    # CREATE
    # ========================================================

    def create(
        self,
        request: InvestigationCreate,
    ) -> Investigation:
        

        target = request.target()

        evidence = self.collector.collect(
            request
        )

        investigation_status = (
            evidence.run_status()
        )

        primary_name = {"namespace": "namespace", "pod": "pod", "deployment": "deployment", "service": "services"}[request.resource_type.value]
        primary = getattr(evidence, primary_name)
        if primary.status == "failed" or (primary_name == "namespace" and isinstance(primary.data, dict) and primary.data.get("found") is False):
            from app.investigations.models import InvestigationStatus
            investigation_status = InvestigationStatus.FAILED

        cluster_context = (
            self._cluster_context()
        )

        analysis = self._build_analysis(
            evidence
        )

        evidence_payload = evidence.model_dump(
            mode="json"
        )

        evidence_payload["analysis"] = (
            analysis.model_dump(
                mode="json"
            )
        )

        record = InvestigationRecord(
            cluster=cluster_context,
            namespace=target.namespace,
            resource_type=(
                target.resource_type.value
            ),
            resource_name=target.resource_name,
            status=investigation_status.value,
            evidence=evidence_payload,
        )

        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)

        except Exception:
            self.db.rollback()
            raise

        return Investigation(
            id=record.id,
            target=target,
            status=investigation_status,
            evidence=evidence,
            analysis=analysis,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    # ========================================================
    # GET
    # ========================================================

    def get(
        self,
        investigation_id: str,
    ) -> Investigation:
        record = self.db.get(
            InvestigationRecord,
            investigation_id,
        )

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Investigation not found.",
            )

        return self._to_investigation(
            record
        )

    # ========================================================
    # LIST
    # ========================================================

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        namespace: str | None = None,
        investigation_status: str | None = None,
        resource_type: str | None = None,
    ) -> InvestigationListResponse:
        query = self.db.query(
            InvestigationRecord
        )

        if namespace:
            query = query.filter(
                InvestigationRecord.namespace
                == namespace
            )

        if investigation_status:
            query = query.filter(
                InvestigationRecord.status
                == investigation_status
            )

        if resource_type:
            query = query.filter(
                InvestigationRecord.resource_type
                == resource_type
            )

        if search and search.strip():
            search_value = (
                f"%{search.strip()}%"
            )

            query = query.filter(
                or_(
                    InvestigationRecord.resource_name.ilike(
                        search_value
                    ),
                    InvestigationRecord.namespace.ilike(
                        search_value
                    ),
                    InvestigationRecord.resource_type.ilike(
                        search_value
                    ),
                    InvestigationRecord.cluster.ilike(
                        search_value
                    ),
                )
            )

        total = query.count()

        records = (
            query.order_by(
                InvestigationRecord.created_at.desc()
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
            .all()
        )

        pages = (
            ceil(total / page_size)
            if total > 0
            else 0
        )

        items = [
            InvestigationListItem(
                id=record.id,
                cluster=record.cluster,
                namespace=record.namespace,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
            for record in records
        ]

        return InvestigationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ========================================================
    # CLUSTER CONTEXT
    # ========================================================

    def _cluster_context(self) -> str:
        if self.cluster_service is None:
            from app.kubernetes.context_manager import KubernetesContextManager
            try:
                return KubernetesContextManager().get_current_context()
            except Exception:
                return "unknown"

        service = self.cluster_service

        method_names = (
            "get_cluster_name",
            "get_context",
            "get_current_context",
            "get_cluster_context",
            "cluster_context",
        )

        for method_name in method_names:
            method = getattr(
                service,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:
                value = method()

                if value is not None:
                    return str(value)

            except Exception:
                continue

        attribute_names = (
            "cluster_name",
            "context",
            "current_context",
            "cluster",
        )

        for attribute_name in attribute_names:
            value = getattr(
                service,
                attribute_name,
                None,
            )

            if value is not None:
                return str(value)

        return "unknown"

    # ========================================================
    # ANALYSIS
    # ========================================================

    def _build_analysis(
        self,
        evidence: InvestigationEvidence,
    ):
        from app.investigations.models import (
            InvestigationAnalysis,
        )

        evidence_dict = evidence.model_dump(
            mode="json"
        )

        result = self.analysis_service.analyze(
            evidence=evidence_dict
        )

        return InvestigationAnalysis(
            diagnostics=result.get(
                "diagnostics",
                [],
            ),
            root_causes=result.get(
                "root_causes",
                [],
            ),
            ai=result.get(
                "ai"
            ),
        )

    # ========================================================
    # CONVERT DATABASE RECORD
    # ========================================================

    def _to_investigation(
        self,
        record: InvestigationRecord,
    ) -> Investigation:
        from app.investigations.models import (
            InvestigationAnalysis,
        )

        raw_evidence = (
            record.evidence
            if isinstance(
                record.evidence,
                dict,
            )
            else {}
        )

        evidence_payload = dict(
            raw_evidence
        )

        analysis_payload = (
            evidence_payload.pop(
                "analysis",
                {},
            )
        )

        try:
            evidence = (
                InvestigationEvidence.model_validate(
                    evidence_payload
                )
            )

        except Exception:
            evidence = (
                InvestigationEvidence.model_validate(
                    self._empty_evidence()
                )
            )

        try:
            analysis = (
                InvestigationAnalysis.model_validate(
                    analysis_payload
                    or {}
                )
            )

        except Exception:
            analysis = (
                InvestigationAnalysis()
            )

        return Investigation(
            id=record.id,
            target={
                "namespace": record.namespace,
                "resource_type": (
                    record.resource_type
                ),
                "resource_name": (
                    record.resource_name
                ),
            },
            status=record.status,
            evidence=evidence,
            analysis=analysis,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    # ========================================================
    # EMPTY EVIDENCE FALLBACK
    # ========================================================

    @staticmethod
    def _empty_evidence():
        section = {
            "status": "skipped",
            "data": None,
            "error": "No evidence available.",
        }

        return {
            "namespace": section,
            "pod": section,
            "deployment": section,
            "replicaset": section,
            "node": section,
            "events": section,
            "logs": section,
            "services": section,
            "pvc": section,
            "metrics": section,
        }