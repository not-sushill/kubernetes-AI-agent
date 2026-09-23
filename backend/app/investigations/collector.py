from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.logging import app_logger
from app.investigations.models import (
    InvestigationCreate,
    InvestigationEvidence,
    InvestigationResourceType,
    InvestigationSection,
)
from app.kubernetes.services.deployment_service import DeploymentService
from app.kubernetes.services.inventory_service import KubernetesInventoryService
from app.kubernetes.services.namespace_service import NamespaceService
from app.kubernetes.services.pod_service import PodService


class InvestigationCollector:
    """
    Collects Kubernetes evidence through the existing service layer.
    """

    def __init__(
        self,
        namespace_service: NamespaceService | None = None,
        pod_service: PodService | None = None,
        deployment_service: DeploymentService | None = None,
        inventory_service: KubernetesInventoryService | None = None,
    ) -> None:
        self.namespace_service = (
            namespace_service
            or NamespaceService()
        )

        self.pod_service = (
            pod_service
            or PodService()
        )

        self.deployment_service = (
            deployment_service
            or DeploymentService()
        )

        self.inventory_service = (
            inventory_service
            or KubernetesInventoryService()
        )

    def collect(self, request: InvestigationCreate) -> InvestigationEvidence:
        ns = request.namespace
        kind = request.resource_type
        section = self._collect_section
        skipped = InvestigationSection.skipped
        limitations: list[str] = []
        namespace = section("namespace", lambda: self._collect_namespace(ns))
        deployment = section("deployment", lambda: self._collect_deployment(request))
        replicasets = section("replicaset", lambda: self.inventory_service.list_replicasets(ns))
        services = section("services", lambda: self.inventory_service.list_services(ns))
        pods = section("pod", lambda: self._collect_pod(request))
        if kind == InvestigationResourceType.SERVICE:
            if isinstance(services.data, list):
                matched = [s for s in services.data if s.get("name") == request.resource_name]
                services = InvestigationSection.collected(matched) if matched else InvestigationSection.failed("Requested Service was not found.")
            deployment = skipped("Not a deployment investigation.")
            replicasets = skipped("Not required for a Service investigation.")
        if kind == InvestigationResourceType.DEPLOYMENT:
            if isinstance(replicasets.data, list) and isinstance(deployment.data, dict):
                target = deployment.data
                replicasets.data = [r for r in replicasets.data if any(
                    o.get("kind") == "Deployment" and o.get("name") == target.get("name")
                    and (not target.get("uid") or o.get("uid") == target["uid"])
                    for o in r.get("owner_references", [])
                )]
            if isinstance(pods.data, list):
                if not isinstance(deployment.data, dict):
                    pods = skipped("Deployment unavailable; related pods cannot be established.")
                else:
                    d = deployment.data
                    rs_names = {r["name"] for r in (replicasets.data or [])}
                    pods.data = [p for p in pods.data if (
                        any(o.get("kind") == "ReplicaSet" and o.get("name") in rs_names for o in p.get("owner_references", []))
                        or (not p.get("owner_references") and self._matches_selector(p.get("labels", {}), d.get("selector", {}), d.get("selector_expressions", [])))
                    )]
        elif kind == InvestigationResourceType.SERVICE and isinstance(pods.data, list):
            if not isinstance(services.data, list) or not services.data:
                pods = skipped("Service unavailable; related pods cannot be established.")
            else:
                selector = services.data[0].get("selector") or {}
                pods.data = [p for p in pods.data if self._matches_selector(p.get("labels", {}), selector)] if selector else []
        selected = [pods.data] if isinstance(pods.data, dict) else (pods.data or [])
        selected = [p for p in selected if isinstance(p, dict)]
        pod_names = {p.get("name") for p in selected}
        if kind in {InvestigationResourceType.POD, InvestigationResourceType.DEPLOYMENT}:
            if isinstance(services.data, list):
                services.data = [s for s in services.data if s.get("selector") and any(
                    self._matches_selector(p.get("labels", {}), s["selector"]) for p in selected
                )]
            if kind == InvestigationResourceType.POD:
                deployment = skipped("Pod investigation; deployment status is not inferred.")
                replicasets = skipped("Pod investigation.")
        nodes = section("node", self.inventory_service.list_nodes)
        node_names = {p.get("node") for p in selected if p.get("node")}
        if kind != InvestigationResourceType.NAMESPACE and isinstance(nodes.data, list):
            nodes.data = [n for n in nodes.data if n.get("name") in node_names]
        events = section("events", lambda: self._collect_scoped_events(request, pod_names, replicasets.data))
        logs = section("logs", lambda: self._collect_scoped_logs(request, selected, limitations))
        pvc = section("pvc", lambda: self.inventory_service.list_persistent_volume_claims(ns))
        if kind != InvestigationResourceType.NAMESPACE and isinstance(pvc.data, list):
            claims = {v.get("persistentVolumeClaim", {}).get("claimName") for p in selected for v in p.get("volumes", [])}
            pvc.data = [p for p in pvc.data if p.get("name") in claims]
        metrics = section("metrics", lambda: self.inventory_service.get_metrics(ns))
        if kind != InvestigationResourceType.NAMESPACE and isinstance(metrics.data, dict):
            metrics.data["pods"] = [p for p in metrics.data.get("pods", []) if p.get("name") in pod_names]
            if kind != InvestigationResourceType.NAMESPACE:
                metrics.data["nodes"] = [n for n in metrics.data.get("nodes", []) if n.get("name") in node_names]
        endpoints = section("endpoints", lambda: self.inventory_service.list_endpoint_slices(ns))
        if kind != InvestigationResourceType.NAMESPACE and isinstance(endpoints.data, list):
            names = {s.get("name") for s in (services.data or [])}
            endpoints.data = [e for e in endpoints.data if e.get("metadata", {}).get("labels", {}).get("kubernetes.io/service-name") in names]
        policies = section("network_policies", lambda: self.inventory_service.list_network_policies(ns))
        quotas = section("resource_quotas", lambda: self.inventory_service.list_resource_quotas(ns))
        return InvestigationEvidence(namespace=namespace, pod=pods, deployment=deployment,
            replicaset=replicasets, node=nodes, events=events, logs=logs, services=services,
            pvc=pvc, metrics=metrics, endpoints=endpoints, network_policies=policies,
            resource_quotas=quotas, limitations=limitations)

    @staticmethod
    def _matches_selector(labels, selector, expressions=None):
        if not selector and not expressions:
            return False
        if any(labels.get(k) != v for k, v in selector.items()):
            return False
        for expression in expressions or []:
            key, operator, values = expression.get("key"), expression.get("operator"), expression.get("values", [])
            if operator == "In" and (key not in labels or labels[key] not in values):
                return False
            if operator == "NotIn" and key in labels and labels[key] in values:
                return False
            if operator == "Exists" and key not in labels:
                return False
            if operator == "DoesNotExist" and key in labels:
                return False
            if operator not in {"In", "NotIn", "Exists", "DoesNotExist"}:
                return False
        return True

    def _collect_scoped_events(self, request, pod_names, replicasets):
        if request.resource_type == InvestigationResourceType.POD:
            return self._collect_events(request)
        events = self.inventory_service.list_namespace_events(request.namespace)
        if request.resource_type == InvestigationResourceType.NAMESPACE:
            return {"events": events}
        allowed = {("Pod", name) for name in pod_names}
        allowed.add((request.resource_type.value.title(), request.resource_name))
        allowed.update(("ReplicaSet", r.get("name")) for r in (replicasets or []))
        return {"events": [e for e in events if (
            e.get("involved_object", {}).get("kind"), e.get("involved_object", {}).get("name")) in allowed]}

    def _collect_scoped_logs(self, request, pods, limitations):
        if not pods:
            return InvestigationSection.skipped("No related pod available for logs.").model_dump(mode="json")
        # Bound collection time and report any omitted pods explicitly.
        ordered = sorted(pods, key=lambda p: (p.get("status") == "Running" and not p.get("restarts"), p.get("name", "")))
        if len(ordered) > 10:
            limitations.append(f"Collected logs from 10 of {len(ordered)} related pods, prioritizing unhealthy pods.")
        output = {}
        for pod in reversed(ordered[:10]):
            pod_request = request.model_copy(update={"resource_type": InvestigationResourceType.POD, "resource_name": pod["name"]})
            try:
                output[pod["name"]] = self._collect_logs(pod_request, pod)
                payload = output[pod["name"]]
                current = payload.get("containers", {})
                if payload.get("available") is False or any(c.get("available") is False for c in current.values()):
                    limitations.append(f"Some current logs were unavailable for pod {pod['name']}.")
                for c in payload.get("previous", {}).values():
                    if c.get("available") is False:
                        limitations.append(f"Some previous logs were unavailable for pod {pod['name']}.")
            except Exception as exc:
                limitations.append(f"Log collection failed for {pod['name']}: {exc}")
                output[pod["name"]] = {"available": False, "logs": [], "message": str(exc)}
        if request.resource_type == InvestigationResourceType.POD:
            return output[request.resource_name]
        return {"pods": output}

    def _collect_namespace(
        self,
        namespace: str,
    ) -> dict[str, Any]:
        namespaces = self.namespace_service.list_namespaces()

        matched_namespace = next(
            (
                item
                for item in namespaces
                if item.get("name") == namespace
            ),
            None,
        )

        return {
            "name": namespace,
            "found": matched_namespace is not None,
            "namespace": matched_namespace,
        }

    def _collect_pod(
        self,
        request: InvestigationCreate,
    ) -> Any:
        if request.resource_type is InvestigationResourceType.POD:
            return self.pod_service.get_pod(
                request.namespace,
                request.resource_name or "",
            )

        return self.pod_service.list_pods(
            request.namespace
        )

    def _collect_deployment(
        self,
        request: InvestigationCreate,
    ) -> Any:
        if request.resource_type is InvestigationResourceType.DEPLOYMENT:
            return self.deployment_service.get_deployment(
                request.namespace,
                request.resource_name or "",
            )

        return self.deployment_service.list_deployments(
            request.namespace
        )

    def _collect_events(
        self,
        request: InvestigationCreate,
    ) -> Any:
        if request.resource_type is InvestigationResourceType.POD:
            return self.pod_service.get_events(
                request.namespace,
                request.resource_name or "",
            )

        if request.resource_type is InvestigationResourceType.DEPLOYMENT:
            return self.deployment_service.get_events(
                request.namespace,
                request.resource_name or "",
            )

        return self.inventory_service.list_namespace_events(
            request.namespace
        )

    def _collect_logs(
        self,
        request: InvestigationCreate,
        pod_data: Any,
    ) -> Any:
        selected_pod = self._select_log_pod(
            request,
            pod_data,
        )

        if selected_pod is None:
            return InvestigationSection.skipped(
                "No pod was available for log collection."
            ).model_dump(
                mode="json"
            )

        selected_pod_data = self._resolve_selected_pod_data(
            request=request,
            selected_pod=selected_pod,
            pod_data=pod_data,
        )

        containers = self._extract_container_names(
            selected_pod_data
        )

        # Fallback for pods where container metadata is unavailable.
        if not containers:
            result = self.pod_service.get_logs(
                namespace=request.namespace,
                pod=selected_pod,
                previous=False,
                tail=request.log_tail,
            )

            return result

        current: dict[str, dict[str, Any]] = {}
        previous: dict[str, dict[str, Any]] = {}

        for container_name in containers:
            current_result = self.pod_service.get_logs(
                namespace=request.namespace,
                pod=selected_pod,
                container=container_name,
                previous=False,
                tail=request.log_tail,
            )

            current[container_name] = current_result

            metadata = next((c for c in (
                (selected_pod_data.get("containers") or [])
                + (selected_pod_data.get("init_containers") or [])
            ) if c.get("name") == container_name), {})
            no_previous_instance = (
                metadata.get("restart_count") == 0
                and not (metadata.get("last_state") or {}).get("terminated")
            )
            if request.include_previous_logs and not no_previous_instance:
                previous_result = self.pod_service.get_logs(
                    namespace=request.namespace,
                    pod=selected_pod,
                    container=container_name,
                    previous=True,
                    tail=request.log_tail,
                )

                previous[container_name] = previous_result

        return {
            "pod": selected_pod,
            "namespace": request.namespace,
            "containers": current,
            "previous": previous,
        }

    def _resolve_selected_pod_data(
        self,
        request: InvestigationCreate,
        selected_pod: str,
        pod_data: Any,
    ) -> Any:
        if request.resource_type is InvestigationResourceType.POD:
            if isinstance(
                pod_data,
                dict,
            ):
                return pod_data

            return self.pod_service.get_pod(
                request.namespace,
                selected_pod,
            )

        if isinstance(
            pod_data,
            list,
        ):
            summary = next(
                (
                    item
                    for item in pod_data
                    if isinstance(item, dict)
                    and item.get("name") == selected_pod
                ),
                None,
            )

            if summary is not None:
                # Namespace pod listings contain only summary data.
                # Fetch the complete pod so container names are known.
                return self.pod_service.get_pod(
                    request.namespace,
                    selected_pod,
                )

        return self.pod_service.get_pod(
            request.namespace,
            selected_pod,
        )

    @staticmethod
    def _extract_container_names(
        pod_data: Any,
    ) -> list[str]:
        if not isinstance(
            pod_data,
            dict,
        ):
            return []

        containers = (
            (pod_data.get("containers") or []) + (pod_data.get("init_containers") or [])
        )

        if not isinstance(
            containers,
            list,
        ):
            return []

        names: list[str] = []

        for container in containers:
            if not isinstance(
                container,
                dict,
            ):
                continue

            name = str(
                container.get("name")
                or ""
            ).strip()

            if not name:
                continue

            if name not in names:
                names.append(name)

        return names

    @staticmethod
    def _select_log_pod(
        request: InvestigationCreate,
        pod_data: Any,
    ) -> str | None:
        if request.resource_type is InvestigationResourceType.POD:
            return request.resource_name

        if not isinstance(
            pod_data,
            list,
        ) or not pod_data:
            return None

        candidate = next(
            (
                pod
                for pod in pod_data
                if isinstance(pod, dict)
                and (
                    pod.get("status") != "Running"
                    or pod.get("restarts", 0) > 0
                )
            ),
            pod_data[0],
        )

        if not isinstance(
            candidate,
            dict,
        ):
            return None

        return candidate.get("name")

    @staticmethod
    def _collect_section(
        section_name: str,
        collector: Callable[[], Any],
    ) -> InvestigationSection:
        try:
            data = collector()

            if (
                isinstance(data, dict)
                and data.get("status") == "skipped"
            ):
                return InvestigationSection.skipped(
                    str(
                        data.get("error")
                        or "Collection skipped."
                    )
                )

            return InvestigationSection.collected(
                data
            )

        except Exception as exc:
            app_logger.warning(
                "Investigation section '{}' failed: {}",
                section_name,
                exc,
            )

            return InvestigationSection.failed(
                getattr(exc, "stderr", None) or str(exc)
            )