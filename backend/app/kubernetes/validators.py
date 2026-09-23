"""
Validation utilities for Kubernetes resources.

All user supplied values MUST be validated before being
passed to the KubectlExecutor.
"""

from __future__ import annotations

import re
from typing import Final

from app.kubernetes.constants import (
    RESOURCE_DAEMONSET,
    RESOURCE_DEPLOYMENT,
    RESOURCE_DEPLOYMENTS,
    RESOURCE_EVENTS,
    RESOURCE_NAMESPACE,
    RESOURCE_NAMESPACES,
    RESOURCE_NODE,
    RESOURCE_NODES,
    RESOURCE_PERSISTENT_VOLUME_CLAIMS,
    RESOURCE_POD,
    RESOURCE_PODS,
    RESOURCE_REPLICASETS,
    RESOURCE_SERVICE,
    RESOURCE_SERVICES,
    RESOURCE_STATEFULSET,
)
from app.kubernetes.exceptions import InvalidKubectlArgumentError

DNS_LABEL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
)

DNS_SUBDOMAIN_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?" r"(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$",
)

SINCE_DURATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[1-9][0-9]*(ns|us|ms|s|m|h)$",
)

MAX_DNS_LABEL_LENGTH: Final[int] = 63
MAX_DNS_SUBDOMAIN_LENGTH: Final[int] = 253
MAX_LOG_TAIL_LINES: Final[int] = 100_000

SUPPORTED_RESOURCE_KINDS: Final[frozenset[str]] = frozenset(
    {
        RESOURCE_DAEMONSET,
        RESOURCE_DEPLOYMENT,
        RESOURCE_DEPLOYMENTS,
        RESOURCE_EVENTS,
        RESOURCE_NAMESPACE,
        RESOURCE_NAMESPACES,
        RESOURCE_NODE,
        RESOURCE_NODES,
        RESOURCE_PERSISTENT_VOLUME_CLAIMS,
        RESOURCE_POD,
        RESOURCE_PODS,
        RESOURCE_REPLICASETS,
        RESOURCE_SERVICE,
        RESOURCE_SERVICES,
        RESOURCE_STATEFULSET,
    },
)


def _validate_dns_name(
    value: str,
    resource_type: str,
    pattern: re.Pattern[str],
    max_length: int,
) -> str:
    """
    Validate a Kubernetes DNS-style name.
    """

    value = value.strip()

    if not value:
        raise InvalidKubectlArgumentError(f"{resource_type} cannot be empty.")

    if len(value) > max_length:
        raise InvalidKubectlArgumentError(
            f"{resource_type} exceeds {max_length} characters."
        )

    if not pattern.fullmatch(value):
        raise InvalidKubectlArgumentError(f"Invalid {resource_type}: '{value}'")

    return value


def validate_namespace(namespace: str) -> str:
    """Validate namespace."""

    return _validate_dns_name(
        namespace,
        "namespace",
        DNS_LABEL_PATTERN,
        MAX_DNS_LABEL_LENGTH,
    )


def validate_pod_name(pod_name: str) -> str:
    """Validate pod name."""

    return validate_object_name(
        pod_name,
        "pod",
    )


def validate_deployment_name(deployment: str) -> str:
    """Validate deployment."""

    return validate_object_name(
        deployment,
        "deployment",
    )


def validate_service_name(service: str) -> str:
    """Validate service."""

    return validate_object_name(
        service,
        "service",
    )


def validate_node_name(node: str) -> str:
    """Validate node."""

    return validate_object_name(
        node,
        "node",
    )


def validate_container_name(container: str) -> str:
    """Validate container name."""

    return _validate_dns_name(
        container,
        "container",
        DNS_LABEL_PATTERN,
        MAX_DNS_LABEL_LENGTH,
    )


def validate_object_name(value: str, resource_type: str = "resource") -> str:
    """Validate a Kubernetes object name."""

    return _validate_dns_name(
        value,
        resource_type,
        DNS_SUBDOMAIN_PATTERN,
        MAX_DNS_SUBDOMAIN_LENGTH,
    )


def validate_resource_kind(resource: str) -> str:
    """Validate a supported kubectl resource kind."""

    resource = resource.strip().lower()

    if resource not in SUPPORTED_RESOURCE_KINDS:
        raise InvalidKubectlArgumentError(
            f"Unsupported Kubernetes resource kind: '{resource}'"
        )

    return resource


def validate_tail_lines(tail: int | None) -> int | None:
    """Validate kubectl log tail line count."""

    if tail is None:
        return None

    if tail < 0:
        raise InvalidKubectlArgumentError(
            "Log tail must be greater than or equal to zero."
        )

    if tail > MAX_LOG_TAIL_LINES:
        raise InvalidKubectlArgumentError(
            f"Log tail cannot exceed {MAX_LOG_TAIL_LINES} lines."
        )

    return tail


def validate_since_duration(since: str | None) -> str | None:
    """Validate kubectl logs --since duration."""

    if since is None:
        return None

    since = since.strip()

    if not since:
        return None

    if not SINCE_DURATION_PATTERN.fullmatch(since):
        raise InvalidKubectlArgumentError(
            "Log since duration must look like '30s', '10m', or '2h'."
        )

    return since


def validate_context(context: str) -> str:
    """Validate kubeconfig context."""

    context = context.strip()

    if not context:
        raise InvalidKubectlArgumentError("context cannot be empty.")

    if any(character.isspace() for character in context):
        raise InvalidKubectlArgumentError(f"Invalid context: '{context}'")

    return context
