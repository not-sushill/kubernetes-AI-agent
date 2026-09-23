from __future__ import annotations

from typing import Any

from app.kubernetes.client import KubectlClient
from app.kubernetes.parser import parse_json_output
from app.kubernetes.services.events import map_event_items


class IngressService:
    """
    Business logic for Kubernetes Ingress operations.
    """

    def __init__(
        self,
        client: KubectlClient | None = None,
    ) -> None:
        self.client = client or KubectlClient()

    # ==========================================================
    # List Ingresses
    # ==========================================================

    def list_ingresses(
        self,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        result = self.client.get_ingresses(namespace)
        data = parse_json_output(result)

        response: list[dict[str, Any]] = []

        for item in data.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            ingress_class = (
                spec.get("ingressClassName")
                or metadata.get("annotations", {}).get(
                    "kubernetes.io/ingress.class",
                    "",
                )
            )

            hosts: list[str] = []

            for rule in spec.get("rules") or []:
                host = rule.get("host")

                if host and host not in hosts:
                    hosts.append(host)

            addresses: list[str] = []

            for load_balancer in (
                status.get("loadBalancer", {}).get("ingress") or []
            ):
                ip = load_balancer.get("ip")
                hostname = load_balancer.get("hostname")

                if ip:
                    addresses.append(ip)
                elif hostname:
                    addresses.append(hostname)

            ports: set[str] = set()

            for rule in spec.get("rules") or []:
                http = rule.get("http") or {}

                for path in http.get("paths") or []:
                    backend = path.get("backend") or {}
                    service = backend.get("service") or {}

                    port = service.get("port") or {}

                    if isinstance(port, dict):
                        port_number = port.get("number")
                        port_name = port.get("name")

                        if port_number is not None:
                            ports.add(str(port_number))
                        elif port_name:
                            ports.add(str(port_name))

            response.append(
                {
                    "namespace": metadata.get("namespace") or "",
                    "name": metadata.get("name") or "",
                    "ingress_class": ingress_class,
                    "hosts": hosts,
                    "address": ", ".join(addresses),
                    "ports": ", ".join(sorted(ports)),
                    "age": metadata.get("creationTimestamp") or "",
                }
            )

        return response

    # ==========================================================
    # Get Ingress Detail
    # ==========================================================

    def get_ingress(
        self,
        namespace: str,
        ingress: str,
    ) -> dict[str, Any]:
        result = self.client.get_ingress(
            namespace,
            ingress,
        )

        data = parse_json_output(result)

        metadata = data.get("metadata", {})
        spec = data.get("spec", {})
        status = data.get("status", {})

        ingress_class = (
            spec.get("ingressClassName")
            or metadata.get("annotations", {}).get(
                "kubernetes.io/ingress.class",
                "",
            )
        )

        addresses: list[str] = []

        for load_balancer in (
            status.get("loadBalancer", {}).get("ingress") or []
        ):
            ip = load_balancer.get("ip")
            hostname = load_balancer.get("hostname")

            if ip:
                addresses.append(ip)
            elif hostname:
                addresses.append(hostname)

        rules: list[dict[str, Any]] = []

        for rule in spec.get("rules") or []:
            host = rule.get("host") or ""
            http = rule.get("http") or {}

            for path in http.get("paths") or []:
                path_value = path.get("path") or "/"
                path_type = path.get("pathType") or ""

                backend = path.get("backend") or {}

                service = backend.get("service") or {}

                service_name = service.get("name") or ""

                service_port = service.get("port") or {}

                if isinstance(service_port, dict):
                    port_number = service_port.get("number")
                    port_name = service_port.get("name")

                    if port_number is not None:
                        port: int | str = port_number
                    elif port_name:
                        port = port_name
                    else:
                        port = ""
                else:
                    port = service_port

                rules.append(
                    {
                        "host": host,
                        "path": (
                            f"{path_value}"
                            f" ({path_type})"
                            if path_type
                            else path_value
                        ),
                        "service": service_name,
                        "port": port,
                    }
                )

        tls: list[dict[str, Any]] = []

        for tls_entry in spec.get("tls") or []:
            tls.append(
                {
                    "hosts": tls_entry.get("hosts") or [],
                    "secret_name": tls_entry.get("secretName") or "",
                }
            )

        return {
            "namespace": metadata.get("namespace") or namespace,
            "name": metadata.get("name") or ingress,
            "ingress_class": ingress_class,
            "address": ", ".join(addresses),
            "rules": rules,
            "tls": tls,
            "labels": metadata.get("labels") or {},
            "annotations": metadata.get("annotations") or {},
        }

    # ==========================================================
    # Events
    # ==========================================================

    def get_events(
        self,
        namespace: str,
        ingress: str,
    ) -> dict[str, Any]:
        result = self.client.get_ingress_events(
            namespace,
            ingress,
        )

        data = parse_json_output(result)

        events = map_event_items(
            data.get("items", [])
        )

        return {
            "namespace": namespace,
            "name": ingress,
            "total_events": len(events),
            "events": events,
        }

    # ==========================================================
    # YAML
    # ==========================================================

    def get_yaml(
        self,
        namespace: str,
        ingress: str,
    ) -> dict[str, Any]:
        result = self.client.get_ingress_yaml(
            namespace,
            ingress,
        )

        return {
            "namespace": namespace,
            "name": ingress,
            "yaml": result.stdout,
        }