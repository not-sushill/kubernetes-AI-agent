from __future__ import annotations

import json

from app.kubernetes.client import KubectlClient


class ServiceService:

    def __init__(
        self,
        client: KubectlClient | None = None,
    ) -> None:

        self.client = (
            client
            or KubectlClient()
        )

    def list_services(
        self,
        namespace: str | None = None,
    ) -> list[dict]:

        result = self.client.get_services(
            namespace,
        )

        data = json.loads(
            result.stdout,
        )

        response: list[dict] = []

        for item in data.get(
            "items",
            [],
        ):

            metadata = item.get(
                "metadata",
                {},
            )

            spec = item.get(
                "spec",
                {},
            )

            status = item.get(
                "status",
                {},
            )

            ports = []

            for port in spec.get(
                "ports",
                [],
            ):

                ports.append(
                    {
                        "name": port.get(
                            "name",
                            "",
                        ),
                        "port": port.get(
                            "port",
                            "",
                        ),
                        "target_port": port.get(
                            "targetPort",
                            "",
                        ),
                        "protocol": port.get(
                            "protocol",
                            "",
                        ),
                    }
                )

            response.append(
                {
                    "namespace": metadata.get(
                        "namespace",
                        "",
                    ),
                    "name": metadata.get(
                        "name",
                        "",
                    ),
                    "type": spec.get(
                        "type",
                        "",
                    ),
                    "cluster_ip": spec.get(
                        "clusterIP",
                        "",
                    ),
                    "external_ip": status.get(
                        "loadBalancer",
                        {},
                    ),
                    "ports": ports,
                    "selector": spec.get(
                        "selector",
                        {},
                    ),
                    "age": metadata.get(
                        "creationTimestamp",
                        "",
                    ),
                }
            )

        return response

    def get_service(
        self,
        namespace: str,
        service: str,
    ) -> dict:

        result = self.client.get_service(
            namespace,
            service,
        )

        return json.loads(
            result.stdout,
        )

    def get_service_yaml(
        self,
        namespace: str,
        service: str,
    ) -> str:

        result = self.client.get_service_yaml(
            namespace,
            service,
        )

        return result.stdout

    def get_events(self, namespace: str, service_name: str) -> dict:
        from app.kubernetes.services.events import map_event_items
        from app.kubernetes.validators import validate_object_name
        validate_object_name(service_name)
        result = self.client.get_namespace_events(namespace)
        data = json.loads(result.stdout)
        items = [
            item for item in data.get("items", [])
            if (item.get("involvedObject") or item.get("regarding") or {}).get("kind") == "Service"
            and (item.get("involvedObject") or item.get("regarding") or {}).get("name") == service_name
        ]
        events = map_event_items(items)
        return {"namespace": namespace, "service": service_name,
                "total_events": len(events), "events": events}
