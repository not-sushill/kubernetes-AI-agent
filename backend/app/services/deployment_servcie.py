"""
Backward-compatible import for the historical misspelled module path.
"""

from app.kubernetes.services.deployment_service import DeploymentService

__all__ = ["DeploymentService"]
