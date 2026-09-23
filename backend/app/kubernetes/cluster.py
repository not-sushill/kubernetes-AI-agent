"""
Backward-compatible import for the historical Kubernetes cluster module.
"""

from app.kubernetes.services.cluster_service import ClusterService

__all__ = ["ClusterService"]
