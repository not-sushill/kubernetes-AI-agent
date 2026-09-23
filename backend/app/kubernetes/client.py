"""
High-level kubectl client.

Responsible for constructing safe kubectl commands.

All command execution is delegated to KubectlExecutor.
"""

from __future__ import annotations

from app.kubernetes.constants import (
    CMD_CLUSTER_INFO,
    CMD_DESCRIBE,
    CMD_GET,
    CMD_LOGS,
    CMD_TOP,
    CMD_VERSION,
    OUTPUT_JSON,
    OUTPUT_YAML,
    RESOURCE_DEPLOYMENT,
    RESOURCE_DEPLOYMENTS,
    RESOURCE_EVENTS,
    RESOURCE_INGRESS,
    RESOURCE_INGRESSES,
    RESOURCE_NAMESPACES,
    RESOURCE_NODES,
    RESOURCE_PERSISTENT_VOLUME_CLAIMS,
    RESOURCE_POD,
    RESOURCE_PODS,
    RESOURCE_REPLICASETS,
    RESOURCE_SERVICES,
)

from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.models import CommandResult

from app.kubernetes.validators import (
    validate_container_name,
    validate_deployment_name,
    validate_namespace,
    validate_object_name,
    validate_pod_name,
    validate_resource_kind,
    validate_since_duration,
    validate_tail_lines,
)


class KubectlClient:
    """
    High-level wrapper around KubectlExecutor.

    This class is responsible only for constructing kubectl commands.
    Actual command execution is delegated to KubectlExecutor.
    """

    def __init__(
        self,
        executor: KubectlExecutor | None = None,
    ) -> None:
        self.executor = executor or KubectlExecutor()

    # ==========================================================
    # Contexts
    # ==========================================================

    def list_contexts(self) -> CommandResult:
        """
        Return all available kubeconfig contexts.
        """

        return self.executor.execute(
            [
                "config",
                "get-contexts",
                "-o",
                "name",
            ]
        )

    def current_context(self) -> CommandResult:
        """
        Return the currently active kubeconfig context.
        """

        return self.executor.execute(
            [
                "config",
                "current-context",
            ]
        )

    def switch_context(
        self,
        context: str,
    ) -> CommandResult:
        """
        Switch the active Kubernetes context.
        """

        return self.executor.execute(
            [
                "config",
                "use-context",
                context,
            ]
        )

    # ==========================================================
    # Cluster
    # ==========================================================

    def version(self) -> CommandResult:
        """
        Return kubectl client/server version.
        """

        return self.executor.execute(
            [
                CMD_VERSION,
                "-o",
                OUTPUT_JSON,
            ]
        )

    def cluster_info(self) -> CommandResult:
        """
        Return cluster information.
        """

        return self.executor.execute(
            [
                CMD_CLUSTER_INFO,
            ]
        )

    # ==========================================================
    # Generic Resources
    # ==========================================================

    def get_resources(
        self,
        resource: str,
        namespace: str | None = None,
    ) -> CommandResult:
        """
        Generic kubectl get for a supported resource type.
        """

        command = [
            CMD_GET,
            validate_resource_kind(resource),
        ]

        if namespace:
            command.extend(
                [
                    "-n",
                    validate_namespace(namespace),
                ]
            )
        else:
            command.append("-A")

        command.extend(
            [
                "-o",
                OUTPUT_JSON,
            ]
        )

        return self.executor.execute(command)

    def describe_resource(
        self,
        resource: str,
        name: str,
        namespace: str | None = None,
    ) -> CommandResult:
        """
        Generic kubectl describe.
        """

        command = [
            CMD_DESCRIBE,
            validate_resource_kind(resource),
            validate_object_name(
                name,
                resource,
            ),
        ]

        if namespace:
            command.extend(
                [
                    "-n",
                    validate_namespace(namespace),
                ]
            )

        return self.executor.execute(command)

    # ==========================================================
    # Namespaces
    # ==========================================================

    def get_namespaces(
        self,
    ) -> CommandResult:
        """
        List Kubernetes namespaces.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_NAMESPACES,
                "-o",
                OUTPUT_JSON,
            ]
        )

    # ==========================================================
    # Pods
    # ==========================================================

    def get_pods(
        self,
        namespace: str | None = None,
    ) -> CommandResult:
        """
        List pods.
        """

        command = [
            CMD_GET,
            RESOURCE_PODS,
        ]

        if namespace:
            command.extend(
                [
                    "-n",
                    validate_namespace(namespace),
                ]
            )
        else:
            command.append("-A")

        command.extend(
            [
                "-o",
                OUTPUT_JSON,
            ]
        )

        return self.executor.execute(command)

    def get_pod(
        self,
        namespace: str,
        pod: str,
    ) -> CommandResult:
        """
        Get a single pod.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_POD,
                validate_pod_name(pod),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )

    def describe_pod(
        self,
        namespace: str,
        pod: str,
    ) -> CommandResult:
        """
        Describe a pod.
        """

        return self.executor.execute(
            [
                CMD_DESCRIBE,
                RESOURCE_POD,
                validate_pod_name(pod),
                "-n",
                validate_namespace(namespace),
            ]
        )

    def get_pod_yaml(
        self,
        namespace: str,
        pod: str,
    ) -> CommandResult:
        """
        Return pod YAML.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_POD,
                validate_pod_name(pod),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_YAML,
            ]
        )

    def logs(
        self,
        pod: str,
        namespace: str,
        container: str | None = None,
        previous: bool = False,
        tail: int | None = None,
        since: str | None = None,
        timestamps: bool = False,
    ) -> CommandResult:
        """
        Get pod logs.
        """

        command = [
            CMD_LOGS,
            validate_pod_name(pod),
            "-n",
            validate_namespace(namespace),
        ]

        if container:
            command.extend(
                [
                    "-c",
                    validate_container_name(container),
                ]
            )

        if previous:
            command.append("--previous")

        validated_tail = validate_tail_lines(tail)

        if validated_tail is not None:
            command.extend(
                [
                    "--tail",
                    str(validated_tail),
                ]
            )

        validated_since = validate_since_duration(since)

        if validated_since:
            command.extend(
                [
                    "--since",
                    validated_since,
                ]
            )

        if timestamps:
            command.append("--timestamps")

        return self.executor.execute(command)

    def get_pod_events(
        self,
        namespace: str,
        pod: str,
    ) -> CommandResult:
        """
        Get events related to a pod.
        """

        pod_name = validate_pod_name(pod)

        selector = (
            "involvedObject.kind=Pod,"
            f"involvedObject.name={pod_name}"
        )

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_EVENTS,
                "-n",
                validate_namespace(namespace),
                "--field-selector",
                selector,
                "-o",
                OUTPUT_JSON,
            ]
        )

    # ==========================================================
    # Pod Exec
    # ==========================================================

    def exec_pod(
        self,
        namespace: str,
        pod: str,
        command: list[str],
        container: str | None = None,
    ) -> CommandResult:
        """
        Execute a non-interactive command inside a pod.

        Example:
            kubectl exec pod-name -n default -- ls -la
        """

        if not command:
            raise ValueError(
                "Exec command cannot be empty."
            )

        kubectl_command = [
            "exec",
            validate_pod_name(pod),
            "-n",
            validate_namespace(namespace),
        ]

        if container:
            kubectl_command.extend(
                [
                    "-c",
                    validate_container_name(container),
                ]
            )

        kubectl_command.append("--")

        kubectl_command.extend(command)

        return self.executor.execute(
            kubectl_command
        )

    def exec_shell(
        self,
        namespace: str,
        pod: str,
        shell: str = "/bin/sh",
        container: str | None = None,
    ) -> CommandResult:
        """
        Execute a shell command inside a pod.

        Note:
        This backend returns command output. A real interactive
        terminal requires WebSocket or terminal streaming support.
        """

        kubectl_command = [
            "exec",
            validate_pod_name(pod),
            "-n",
            validate_namespace(namespace),
        ]

        if container:
            kubectl_command.extend(
                [
                    "-c",
                    validate_container_name(container),
                ]
            )

        kubectl_command.extend(
            [
                "--",
                shell,
            ]
        )

        return self.executor.execute(
            kubectl_command
        )

    # ==========================================================
    # Deployments
    # ==========================================================

    def get_deployments(
        self,
        namespace: str | None = None,
    ) -> CommandResult:
        """
        List deployments.
        """

        command = [
            CMD_GET,
            RESOURCE_DEPLOYMENTS,
        ]

        if namespace:
            command.extend(
                [
                    "-n",
                    validate_namespace(namespace),
                ]
            )
        else:
            command.append("-A")

        command.extend(
            [
                "-o",
                OUTPUT_JSON,
            ]
        )

        return self.executor.execute(command)

    def get_deployment(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        """
        Get a single deployment.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_DEPLOYMENT,
                validate_deployment_name(
                    deployment
                ),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )

    def describe_deployment(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        """
        Describe a deployment.
        """

        return self.executor.execute(
            [
                CMD_DESCRIBE,
                RESOURCE_DEPLOYMENT,
                validate_deployment_name(
                    deployment
                ),
                "-n",
                validate_namespace(namespace),
            ]
        )

    def get_deployment_events(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        """
        Get deployment-related events.
        """

        deployment_name = validate_deployment_name(
            deployment
        )

        selector = (
            "involvedObject.kind=Deployment,"
            f"involvedObject.name={deployment_name}"
        )

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_EVENTS,
                "-n",
                validate_namespace(namespace),
                "--field-selector",
                selector,
                "-o",
                OUTPUT_JSON,
            ]
        )

    def get_deployment_yaml(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        """
        Return deployment YAML.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_DEPLOYMENT,
                validate_deployment_name(
                    deployment
                ),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_YAML,
            ]
        )

    def validate_deployment_yaml(
        self,
        yaml_path: str,
    ) -> CommandResult:
        """
        Validate deployment YAML using kubectl dry-run.
        """

        return self.executor.execute(
            [
                "apply",
                "--dry-run=server",
                "-f",
                yaml_path,
            ]
        )

    def apply_deployment_yaml(
        self,
        yaml_path: str,
    ) -> CommandResult:
        """
        Apply deployment YAML.
        """

        return self.executor.execute(
            [
                "apply",
                "-f",
                yaml_path,
            ]
        )

    def rollout_status(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        """
        Return rollout status with a timeout.
        """

        return self.executor.execute(
            [
                "rollout",
                "status",
                f"deployment/{validate_deployment_name(deployment)}",
                "-n",
                validate_namespace(namespace),
                "--timeout=60s",
            ],
            timeout=75,
        )

    def get_replicasets(
        self,
        namespace: str,
    ) -> CommandResult:
        """
        List ReplicaSets.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_REPLICASETS,
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )
        # ==========================================================
    # Nodes
    # ==========================================================

    def get_nodes(
        self,
    ) -> CommandResult:
        """
        List Kubernetes nodes.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_NODES,
                "-o",
                OUTPUT_JSON,
            ]
        )

    def get_node(
        self,
        node: str,
    ) -> CommandResult:
        """
        Get a single node.
        """

        return self.executor.execute(
            [
                CMD_GET,
                "node",
                validate_object_name(
                    node,
                    "node",
                ),
                "-o",
                OUTPUT_JSON,
            ]
        )

    def describe_node(
        self,
        node: str,
    ) -> CommandResult:
        """
        Describe a node.
        """

        return self.executor.execute(
            [
                CMD_DESCRIBE,
                "node",
                validate_object_name(
                    node,
                    "node",
                ),
            ]
        )

    def get_node_yaml(
        self,
        node: str,
    ) -> CommandResult:
        """
        Return node YAML.
        """

        return self.executor.execute(
            [
                CMD_GET,
                "node",
                validate_object_name(
                    node,
                    "node",
                ),
                "-o",
                OUTPUT_YAML,
            ]
        )

    def top_nodes(
        self,
    ) -> CommandResult:
        """
        Return node metrics.
        """

        return self.executor.execute(
            [
                CMD_TOP,
                "nodes",
                "--no-headers",
            ]
        )

    def cordon_node(
        self,
        node: str,
    ) -> CommandResult:
        """
        Cordon a node.
        """

        return self.executor.execute(
            [
                "cordon",
                validate_object_name(
                    node,
                    "node",
                ),
            ]
        )

    def uncordon_node(
        self,
        node: str,
    ) -> CommandResult:
        """
        Uncordon a node.
        """

        return self.executor.execute(
            [
                "uncordon",
                validate_object_name(
                    node,
                    "node",
                ),
            ]
        )

    def drain_node(
        self,
        node: str,
    ) -> CommandResult:
        """
        Drain a node.
        """

        return self.executor.execute(
            [
                "drain",
                validate_object_name(
                    node,
                    "node",
                ),
                "--ignore-daemonsets",
                "--delete-emptydir-data",
            ]
        )

    # ==========================================================
    # Services
    # ==========================================================

    def get_services(
        self,
        namespace: str | None = None,
    ) -> CommandResult:
        """
        List Kubernetes services.
        """

        command = [
            CMD_GET,
            RESOURCE_SERVICES,
        ]

        if namespace:
            command.extend(
                [
                    "-n",
                    validate_namespace(namespace),
                ]
            )
        else:
            command.append("-A")

        command.extend(
            [
                "-o",
                OUTPUT_JSON,
            ]
        )

        return self.executor.execute(command)

    def get_service(
        self,
        namespace: str,
        service: str,
    ) -> CommandResult:
        """
        Get a single service.
        """

        return self.executor.execute(
            [
                CMD_GET,
                "service",
                validate_object_name(
                    service,
                    "service",
                ),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )

    def get_service_yaml(
        self,
        namespace: str,
        service: str,
    ) -> CommandResult:
        """
        Return service YAML.
        """

        return self.executor.execute(
            [
                CMD_GET,
                "service",
                validate_object_name(
                    service,
                    "service",
                ),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_YAML,
            ]
        )

    # ==========================================================
    # Metrics
    # ==========================================================

    def top_pods(
        self,
        namespace: str,
    ) -> CommandResult:
        """
        Return pod metrics.
        """

        return self.executor.execute(
            [
                CMD_TOP,
                "pods",
                "-n",
                validate_namespace(namespace),
                "--no-headers",
            ]
        )

    # ==========================================================
    # Storage
    # ==========================================================

    def get_persistent_volume_claims(
        self,
        namespace: str,
    ) -> CommandResult:
        """
        List PersistentVolumeClaims.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_PERSISTENT_VOLUME_CLAIMS,
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )
        # ==========================================================
    # Ingresses
    # ==========================================================

    def get_ingresses(
        self,
        namespace: str | None = None,
    ) -> CommandResult:
        """
        List Kubernetes Ingress resources.
        """

        command = [
            CMD_GET,
            RESOURCE_INGRESSES,
        ]

        if namespace:
            command.extend(
                [
                    "-n",
                    validate_namespace(namespace),
                ]
            )
        else:
            command.append("-A")

        command.extend(
            [
                "-o",
                OUTPUT_JSON,
            ]
        )

        return self.executor.execute(command)

    def get_ingress(
        self,
        namespace: str,
        ingress: str,
    ) -> CommandResult:
        """
        Get a single Kubernetes Ingress.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_INGRESS,
                validate_object_name(
                    ingress,
                    "ingress",
                ),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )

    def get_ingress_yaml(
        self,
        namespace: str,
        ingress: str,
    ) -> CommandResult:
        """
        Return Kubernetes Ingress YAML.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_INGRESS,
                validate_object_name(
                    ingress,
                    "ingress",
                ),
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_YAML,
            ]
        )

    def get_ingress_events(
        self,
        namespace: str,
        ingress: str,
    ) -> CommandResult:
        """
        Get Kubernetes events for an Ingress.
        """

        ingress_name = validate_object_name(
            ingress,
            "ingress",
        )

        selector = (
            "involvedObject.kind=Ingress,"
            f"involvedObject.name={ingress_name}"
        )

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_EVENTS,
                "-n",
                validate_namespace(namespace),
                "--field-selector",
                selector,
                "-o",
                OUTPUT_JSON,
            ]
        )

    # ==========================================================
    # Events
    # ==========================================================

    def get_namespace_events(
        self,
        namespace: str,
    ) -> CommandResult:
        """
        Return events from a namespace.
        """

        return self.executor.execute(
            [
                CMD_GET,
                RESOURCE_EVENTS,
                "-n",
                validate_namespace(namespace),
                "-o",
                OUTPUT_JSON,
            ]
        )

    def get_endpoint_slices(self, namespace: str) -> CommandResult:
        return self.executor.execute(["get", "endpointslices.discovery.k8s.io", "-n", validate_namespace(namespace), "-o", "json"])

    def get_network_policies(self, namespace: str) -> CommandResult:
        return self.executor.execute(["get", "networkpolicies", "-n", validate_namespace(namespace), "-o", "json"])

    def get_resource_quotas(self, namespace: str) -> CommandResult:
        return self.executor.execute(["get", "resourcequotas", "-n", validate_namespace(namespace), "-o", "json"])
