from __future__ import annotations

from app.kubernetes.models import CommandResult
from app.kubernetes.services.deployment_service import DeploymentService
from app.kubernetes.services.pod_service import PodService


def command_result(stdout: str) -> CommandResult:
    return CommandResult(
        command="kubectl get",
        stdout=stdout,
        stderr="",
        return_code=0,
        duration_ms=1.0,
    )


class FakePodClient:
    def get_pods(self, namespace: str | None = None) -> CommandResult:
        return command_result(
            """
            {
              "items": [
                {
                  "metadata": {
                    "namespace": "default",
                    "name": "api",
                    "creationTimestamp": "2026-01-01T00:00:00Z"
                  },
                  "spec": {
                    "nodeName": "worker-1"
                  },
                  "status": {
                    "phase": "Running",
                    "podIP": "10.0.0.10",
                    "containerStatuses": [
                      {
                        "name": "api",
                        "ready": true,
                        "restartCount": 2
                      },
                      {
                        "name": "sidecar",
                        "ready": false,
                        "restartCount": 1
                      }
                    ]
                  }
                }
              ]
            }
            """
        )


class FakeDeploymentClient:
    def get_deployments(
        self,
        namespace: str | None = None,
    ) -> CommandResult:
        return command_result(
            """
            {
              "items": [
                {
                  "metadata": {
                    "namespace": "default",
                    "name": "api",
                    "creationTimestamp": "2026-01-01T00:00:00Z"
                  },
                  "spec": {
                    "replicas": 3,
                    "strategy": {
                      "type": "RollingUpdate"
                    }
                  },
                  "status": {
                    "readyReplicas": 2,
                    "availableReplicas": 2,
                    "updatedReplicas": 3
                  }
                }
              ]
            }
            """
        )

    def get_deployment(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        return command_result(
            """
            {
              "metadata": {
                "namespace": "default",
                "name": "api",
                "labels": {
                  "app": "api"
                },
                "annotations": {
                  "owner": "platform"
                },
                "creationTimestamp": "2026-01-01T00:00:00Z"
              },
              "spec": {
                "replicas": 3,
                "selector": {
                  "matchLabels": {
                    "app": "api"
                  }
                },
                "strategy": {
                  "type": "RollingUpdate"
                },
                "template": {
                  "spec": {
                    "containers": [
                      {
                        "name": "api",
                        "image": "registry.example.com/api:v1"
                      }
                    ]
                  }
                }
              },
              "status": {
                "readyReplicas": 2,
                "availableReplicas": 2,
                "updatedReplicas": 3,
                "conditions": [
                  {
                    "type": "Available",
                    "status": "True",
                    "reason": "MinimumReplicasAvailable",
                    "message": "Deployment has minimum availability.",
                    "lastTransitionTime": "2026-01-01T00:01:00Z"
                  }
                ]
              }
            }
            """
        )

    def get_deployment_events(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        return command_result(
            """
            {
              "items": [
                {
                  "type": "Normal",
                  "reason": "ScalingReplicaSet",
                  "message": "Scaled up replica set api-abc to 3.",
                  "count": 1,
                  "firstTimestamp": "2026-01-01T00:00:00Z",
                  "lastTimestamp": "2026-01-01T00:00:00Z"
                }
              ]
            }
            """
        )

    def get_deployment_yaml(
        self,
        namespace: str,
        deployment: str,
    ) -> CommandResult:
        return command_result("apiVersion: apps/v1\nkind: Deployment\n")


def test_pod_service_maps_pod_list_payload() -> None:
    service = PodService(client=FakePodClient())  # type: ignore[arg-type]

    pods = service.list_pods(namespace="default")

    assert [{k: p[k] for k in ("namespace", "name", "status", "ready", "restarts", "node", "pod_ip", "age")} for p in pods] == [
        {
            "namespace": "default",
            "name": "api",
            "status": "Running",
            "ready": "1/2",
            "restarts": 3,
            "node": "worker-1",
            "pod_ip": "10.0.0.10",
            "age": "2026-01-01T00:00:00Z",
        }
    ]


def test_deployment_service_maps_deployment_list_payload() -> None:
    service = DeploymentService(
        client=FakeDeploymentClient(),  # type: ignore[arg-type]
    )

    deployments = service.list_deployments(namespace="default")

    assert [{k: d[k] for k in ("namespace", "name", "replicas", "ready_replicas", "available_replicas", "updated_replicas", "strategy", "age")} for d in deployments] == [
        {
            "namespace": "default",
            "name": "api",
            "replicas": 3,
            "ready_replicas": 2,
            "available_replicas": 2,
            "updated_replicas": 3,
            "strategy": "RollingUpdate",
            "age": "2026-01-01T00:00:00Z",
        }
    ]


def test_deployment_service_maps_deployment_detail_payload() -> None:
    service = DeploymentService(
        client=FakeDeploymentClient(),  # type: ignore[arg-type]
    )

    deployment = service.get_deployment("default", "api")

    assert deployment["name"] == "api"
    assert deployment["selector"] == {"app": "api"}
    assert deployment["labels"] == {"app": "api"}
    assert deployment["annotations"] == {"owner": "platform"}
    assert deployment["containers"] == [
        {
            "name": "api",
            "image": "registry.example.com/api:v1",
        }
    ]
    assert deployment["conditions"] == [
        {
            "type": "Available",
            "status": "True",
            "reason": "MinimumReplicasAvailable",
            "message": "Deployment has minimum availability.",
            "last_transition_time": "2026-01-01T00:01:00Z",
        }
    ]


def test_deployment_service_maps_events_and_yaml() -> None:
    service = DeploymentService(
        client=FakeDeploymentClient(),  # type: ignore[arg-type]
    )

    events = service.get_events("default", "api")
    yaml_payload = service.get_yaml("default", "api")

    assert events["deployment"] == "api"
    assert events["total_events"] == 1
    assert events["events"][0]["reason"] == "ScalingReplicaSet"
    assert yaml_payload == {
        "deployment": "api",
        "namespace": "default",
        "yaml": "apiVersion: apps/v1\nkind: Deployment\n",
    }
