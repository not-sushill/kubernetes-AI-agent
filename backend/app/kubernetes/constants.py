"""
Constants used throughout the Kubernetes integration layer.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------
# Kubectl
# ---------------------------------------------------------------------

KUBECTL_BINARY: Final[str] = "kubectl"

DEFAULT_TIMEOUT_SECONDS: Final[int] = 30

DEFAULT_RETRY_COUNT: Final[int] = 1

DEFAULT_OUTPUT_FORMAT: Final[str] = "json"

# ---------------------------------------------------------------------
# Supported Output Formats
# ---------------------------------------------------------------------

OUTPUT_JSON: Final[str] = "json"

OUTPUT_YAML: Final[str] = "yaml"

OUTPUT_WIDE: Final[str] = "wide"

OUTPUT_NAME: Final[str] = "name"

# ---------------------------------------------------------------------
# Supported Kubernetes Resources
# ---------------------------------------------------------------------

RESOURCE_POD: Final[str] = "pod"

RESOURCE_PODS: Final[str] = "pods"

RESOURCE_NODE: Final[str] = "node"

RESOURCE_NODES: Final[str] = "nodes"

RESOURCE_NAMESPACE: Final[str] = "namespace"

RESOURCE_NAMESPACES: Final[str] = "namespaces"

RESOURCE_DEPLOYMENT: Final[str] = "deployment"

RESOURCE_DEPLOYMENTS: Final[str] = "deployments"

RESOURCE_REPLICASETS: Final[str] = "replicasets"

RESOURCE_SERVICE: Final[str] = "service"

RESOURCE_SERVICES: Final[str] = "services"

RESOURCE_PERSISTENT_VOLUME_CLAIMS: Final[str] = "persistentvolumeclaims"

RESOURCE_STATEFULSET: Final[str] = "statefulset"

RESOURCE_DAEMONSET: Final[str] = "daemonset"

RESOURCE_EVENTS: Final[str] = "events"

RESOURCE_INGRESSES = "ingresses"

RESOURCE_INGRESS = "ingress"

# ---------------------------------------------------------------------
# Common Kubectl Commands
# ---------------------------------------------------------------------

CMD_GET: Final[str] = "get"

CMD_DESCRIBE: Final[str] = "describe"

CMD_LOGS: Final[str] = "logs"

CMD_VERSION: Final[str] = "version"

CMD_CLUSTER_INFO: Final[str] = "cluster-info"

CMD_TOP: Final[str] = "top"

CMD_APPLY: Final[str] = "apply"

CMD_DELETE: Final[str] = "delete"

# ---------------------------------------------------------------------
# Exit Codes
# ---------------------------------------------------------------------

SUCCESS_EXIT_CODE: Final[int] = 0
