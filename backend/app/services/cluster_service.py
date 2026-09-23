"""
Backward-compatible import for the historical service module path.
"""

from app.kubernetes.services.cluster_service import ClusterService

__all__ = ["ClusterService"]
