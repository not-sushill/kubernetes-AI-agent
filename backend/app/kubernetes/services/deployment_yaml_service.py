from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.kubernetes.client import KubectlClient
from app.kubernetes.exceptions import KubernetesError, KubectlTimeoutError


BACKUP_ROOT = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "deployment-backups"
)


class DeploymentYamlService:
    """Service for validating, applying, backing up, and restoring Deployments."""

    def __init__(
        self,
        client: KubectlClient | None = None,
    ) -> None:
        self.client = client or KubectlClient()

    def prepare_yaml(
        self,
        namespace: str,
        deployment: str,
        yaml_content: str,
    ) -> str:
        """
        Parse and normalize a Deployment YAML manifest.

        Runtime-generated Kubernetes fields are removed before
        validation or application.
        """

        repaired_yaml = self._repair_yaml(
            yaml_content
        )

        document = self._parse(
            repaired_yaml
        )

        self._validate_identity(
            document,
            namespace,
            deployment,
        )

        self._normalize_deployment(
            document
        )

        return yaml.safe_dump(
            document,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
            allow_unicode=True,
        )

    @staticmethod
    def _repair_yaml(
        yaml_content: str,
    ) -> str:
        """
        Perform only safe YAML cleanup.

        This method intentionally does not attempt to guess complex
        indentation problems because aggressive automatic repair can
        move Kubernetes fields into invalid locations.

        Safe operations:
        - Convert tabs to spaces.
        - Remove trailing whitespace.
        - Remove leading/trailing empty lines.
        - Normalize parseable YAML using PyYAML.
        """

        if not yaml_content.strip():
            raise ValueError(
                "YAML cannot be empty."
            )

        lines: list[str] = []

        for line in yaml_content.splitlines():
            cleaned_line = (
                line
                .replace("\t", "  ")
                .rstrip()
            )

            lines.append(
                cleaned_line
            )

        repaired_yaml = "\n".join(
            lines
        ).strip()

        if not repaired_yaml:
            raise ValueError(
                "YAML cannot be empty."
            )

        repaired_yaml += "\n"

        try:
            document = yaml.safe_load(
                repaired_yaml
            )

        except yaml.YAMLError:
            # Let _parse provide the detailed error.
            return repaired_yaml

        if isinstance(
            document,
            dict,
        ):
            return yaml.safe_dump(
                document,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
                allow_unicode=True,
            )

        return repaired_yaml

    @staticmethod
    def _parse(
        yaml_content: str,
    ) -> dict[str, Any]:
        """Parse exactly one Kubernetes YAML object."""

        if not yaml_content.strip():
            raise ValueError(
                "YAML cannot be empty."
            )

        try:
            document = yaml.safe_load(
                yaml_content
            )

        except yaml.YAMLError as exc:
            raise ValueError(
                "Invalid YAML after automatic repair: "
                f"{exc}"
            ) from exc

        if not isinstance(
            document,
            dict,
        ):
            raise ValueError(
                "YAML must contain exactly one "
                "Kubernetes object."
            )

        return document

    @staticmethod
    def _validate_identity(
        document: dict[str, Any],
        namespace: str,
        deployment: str,
    ) -> None:
        """Ensure the edited object remains the selected Deployment."""

        if document.get(
            "kind"
        ) != "Deployment":
            raise ValueError(
                "Resource kind must remain Deployment."
            )

        if document.get(
            "apiVersion"
        ) != "apps/v1":
            raise ValueError(
                "Deployment apiVersion must be apps/v1."
            )

        metadata = document.get(
            "metadata"
        )

        if not isinstance(
            metadata,
            dict,
        ):
            raise ValueError(
                "Deployment metadata is required."
            )

        if metadata.get(
            "name"
        ) != deployment:
            raise ValueError(
                "Deployment name cannot be changed."
            )

        yaml_namespace = metadata.get(
            "namespace",
            namespace,
        )

        if yaml_namespace != namespace:
            raise ValueError(
                "Deployment namespace cannot be changed."
            )

        metadata["namespace"] = namespace

    def _normalize_deployment(
        self,
        document: dict[str, Any],
    ) -> None:
        """
        Remove runtime-only fields from a Deployment.

        This is important when YAML originates from:

            kubectl get deployment ... -o yaml

        because live Kubernetes YAML contains fields that cannot be
        applied as part of a clean Deployment manifest.
        """

        self._remove_generated_fields(
            document
        )

        spec = document.get(
            "spec"
        )

        if not isinstance(
            spec,
            dict,
        ):
            raise ValueError(
                "Deployment spec is required."
            )

        self._remove_runtime_deployment_fields(
            spec
        )

        template = spec.get(
            "template"
        )

        if not isinstance(
            template,
            dict,
        ):
            raise ValueError(
                "Deployment spec.template is required."
            )

        self._normalize_template(
            template
        )

    @staticmethod
    def _remove_generated_fields(
        document: dict[str, Any],
    ) -> None:
        """Remove top-level Kubernetes runtime fields."""

        document.pop(
            "status",
            None,
        )

        metadata = document.get(
            "metadata"
        )

        if isinstance(
            metadata,
            dict,
        ):
            DeploymentYamlService._clean_metadata(
                metadata
            )

    @staticmethod
    def _clean_metadata(
        metadata: dict[str, Any],
    ) -> None:
        """Remove generated metadata fields."""

        generated_fields = (
            "creationTimestamp",
            "deletionGracePeriodSeconds",
            "deletionTimestamp",
            "generation",
            "managedFields",
            "resourceVersion",
            "selfLink",
            "uid",
        )

        for field in generated_fields:
            metadata.pop(
                field,
                None,
            )

        annotations = metadata.get(
            "annotations"
        )

        if isinstance(
            annotations,
            dict,
        ):
            annotations.pop(
                "kubectl.kubernetes.io/"
                "last-applied-configuration",
                None,
            )

            if not annotations:
                metadata.pop(
                    "annotations",
                    None,
                )

    @staticmethod
    def _remove_runtime_deployment_fields(
        spec: dict[str, Any],
    ) -> None:
        """
        Remove fields that belong to Deployment status but may appear
        incorrectly inside spec after copied or malformed YAML.
        """

        runtime_fields = (
            "availableReplicas",
            "conditions",
            "collisionCount",
            "observedGeneration",
            "readyReplicas",
            "terminatingReplicas",
            "unavailableReplicas",
            "updatedReplicas",
        )

        for field in runtime_fields:
            spec.pop(
                field,
                None,
            )

    def _normalize_template(
        self,
        template: dict[str, Any],
    ) -> None:
        """
        Clean Deployment spec.template.

        A valid Deployment template has:

            spec:
              template:
                metadata:
                spec:

        Pod runtime fields accidentally placed in template.metadata
        are moved into template.spec.
        """

        template.pop(
            "status",
            None,
        )

        metadata = template.get(
            "metadata"
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}
            template["metadata"] = metadata

        self._clean_metadata(
            metadata
        )

        template_spec = template.get(
            "spec"
        )

        if not isinstance(
            template_spec,
            dict,
        ):
            template_spec = {}
            template["spec"] = template_spec

        self._move_misplaced_pod_fields(
            metadata,
            template_spec,
        )

        self._remove_runtime_pod_fields(
            template_spec
        )

    @staticmethod
    def _move_misplaced_pod_fields(
        metadata: dict[str, Any],
        pod_spec: dict[str, Any],
    ) -> None:
        """
        Move known PodSpec fields accidentally nested under
        template.metadata into template.spec.

        This handles errors such as:

            spec:
              template:
                metadata:
                  labels:
                    app: example
                  containers:
                    - name: app

        which should become:

            spec:
              template:
                metadata:
                  labels:
                    app: example
                spec:
                  containers:
                    - name: app
        """

        pod_spec_fields = {
            "activeDeadlineSeconds",
            "affinity",
            "automountServiceAccountToken",
            "containers",
            "dnsConfig",
            "dnsPolicy",
            "enableServiceLinks",
            "ephemeralContainers",
            "hostAliases",
            "hostIPC",
            "hostNetwork",
            "hostPID",
            "hostUsers",
            "hostname",
            "imagePullSecrets",
            "initContainers",
            "nodeName",
            "nodeSelector",
            "os",
            "overhead",
            "preemptionPolicy",
            "priority",
            "priorityClassName",
            "readinessGates",
            "restartPolicy",
            "runtimeClassName",
            "schedulerName",
            "securityContext",
            "serviceAccount",
            "serviceAccountName",
            "setHostnameAsFQDN",
            "shareProcessNamespace",
            "subdomain",
            "terminationGracePeriodSeconds",
            "tolerations",
            "topologySpreadConstraints",
            "volumes",
        }

        for field in list(
            metadata.keys()
        ):
            if field not in pod_spec_fields:
                continue

            value = metadata.pop(
                field
            )

            if field not in pod_spec:
                pod_spec[field] = value

    @staticmethod
    def _remove_runtime_pod_fields(
        pod_spec: dict[str, Any],
    ) -> None:
        """Remove fields that cannot belong to PodSpec."""

        pod_spec.pop(
            "status",
            None,
        )

    def _create_temp_yaml_file(
        self,
        yaml_content: str,
    ) -> str:
        """Create a temporary YAML file for kubectl."""

        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            encoding="utf-8",
            delete=False,
        )

        try:
            temp_file.write(
                yaml_content
            )

            temp_file.flush()

            return temp_file.name

        finally:
            temp_file.close()

    def validate(
        self,
        namespace: str,
        deployment: str,
        yaml_content: str,
    ) -> dict[str, Any]:
        """
        Validate the Deployment against the Kubernetes API server.
        """

        formatted = self.prepare_yaml(
            namespace,
            deployment,
            yaml_content,
        )

        yaml_path = self._create_temp_yaml_file(
            formatted
        )

        try:
            result = (
                self.client
                .validate_deployment_yaml(
                    yaml_path
                )
            )

            return {
                "valid": True,
                "formatted_yaml": formatted,
                "message": (
                    result.stdout.strip()
                    or "Server-side validation passed."
                ),
            }

        finally:
            if os.path.exists(
                yaml_path
            ):
                os.remove(
                    yaml_path
                )

    def apply(
        self,
        namespace: str,
        deployment: str,
        yaml_content: str,
    ) -> dict[str, Any]:
        """
        Validate, back up, apply, and wait for rollout completion.
        """

        validation = self.validate(
            namespace,
            deployment,
            yaml_content,
        )

        formatted = validation[
            "formatted_yaml"
        ]

        yaml_path = self._create_temp_yaml_file(
            formatted
        )

        try:
            live = (
                self.client
                .get_deployment_yaml(
                    namespace,
                    deployment,
                )
                .stdout
            )

            backup = self._create_backup(
                namespace=namespace,
                deployment=deployment,
                yaml_content=live,
                reason="pre-apply-backup",
            )

            try:
                apply_result = self.client.apply_deployment_yaml(yaml_path)
            except KubectlTimeoutError as exc:
                saved_id = backup["id"]
                raise KubectlTimeoutError(
                    f"Apply command timed out; outcome unknown. Backup: {saved_id}. "
                    "Check the live deployment before retrying."
                ) from exc

            rollout = self._verify_rollout(namespace, deployment)

            return {
                "success": rollout["rollout_status"] == "completed",
                "applied": True,
                **rollout,
                "deployment": deployment,
                "namespace": namespace,
                "backup_id": backup["id"],
                "apply_output": (
                    apply_result.stdout.strip()
                ),

            }

        finally:
            if os.path.exists(
                yaml_path
            ):
                os.remove(
                    yaml_path
                )

    def _verify_rollout(self, namespace: str, deployment: str) -> dict[str, str]:
        try:
            result = self.client.rollout_status(namespace, deployment)
            return {
                "rollout_status": "completed",
                "rollout_output": result.stdout.strip(),
                "message": "YAML applied and rollout completed.",
            }
        except KubernetesError as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            return {
                "rollout_status": "unconfirmed",
                "rollout_output": detail,
                "message": "YAML applied; rollout not confirmed. Check deployment status before applying again. " + detail,
            }

    def list_backups(
        self,
        namespace: str,
        deployment: str,
    ) -> list[dict[str, Any]]:
        """Return all backups for a Deployment."""

        directory = self._backup_directory(
            namespace,
            deployment,
        )

        if not directory.exists():
            return []

        backups: list[
            dict[str, Any]
        ] = []

        for metadata_file in sorted(
            directory.glob("*.json"),
            reverse=True,
        ):
            try:
                metadata = json.loads(
                    metadata_file.read_text(
                        encoding="utf-8"
                    )
                )

                backups.append(
                    metadata
                )

            except (
                OSError,
                json.JSONDecodeError,
            ):
                continue

        return backups

    def get_backup(
        self,
        namespace: str,
        deployment: str,
        backup_id: str,
    ) -> dict[str, Any]:
        """Return backup metadata and YAML."""

        self._validate_backup_id(
            backup_id
        )

        directory = self._backup_directory(
            namespace,
            deployment,
        )

        yaml_path = (
            directory
            / f"{backup_id}.yaml"
        )

        metadata_path = (
            directory
            / f"{backup_id}.json"
        )

        if (
            not yaml_path.exists()
            or not metadata_path.exists()
        ):
            raise ValueError(
                "Backup not found."
            )

        return {
            "metadata": json.loads(
                metadata_path.read_text(
                    encoding="utf-8"
                )
            ),
            "yaml": yaml_path.read_text(
                encoding="utf-8"
            ),
        }

    def restore(
        self,
        namespace: str,
        deployment: str,
        backup_id: str,
    ) -> dict[str, Any]:
        """
        Restore a Deployment backup.

        The current live Deployment is backed up before restoration.
        """

        backup = self.get_backup(
            namespace,
            deployment,
            backup_id,
        )

        validation = self.validate(
            namespace,
            deployment,
            backup["yaml"],
        )

        restored_yaml = validation[
            "formatted_yaml"
        ]

        yaml_path = self._create_temp_yaml_file(
            restored_yaml
        )

        try:
            current_live = (
                self.client
                .get_deployment_yaml(
                    namespace,
                    deployment,
                )
                .stdout
            )

            recovery_backup = self._create_backup(
                namespace=namespace,
                deployment=deployment,
                yaml_content=current_live,
                reason=(
                    f"pre-restore-{backup_id}"
                ),
            )

            try:
                apply_result = self.client.apply_deployment_yaml(yaml_path)
            except KubectlTimeoutError as exc:
                saved_id = recovery_backup["id"]
                raise KubectlTimeoutError(
                    f"Apply command timed out; outcome unknown. Backup: {saved_id}. "
                    "Check the live deployment before retrying."
                ) from exc

            rollout = self._verify_rollout(namespace, deployment)
            if rollout["rollout_status"] == "completed":
                rollout["message"] = f"Rollback restored from backup {backup_id}; rollout completed."
            else:
                rollout["message"] = (
                    f"Backup {backup_id} applied; rollback rollout not confirmed. "
                    "Check deployment status before retrying. " + rollout["rollout_output"]
                )

            return {
                "success": rollout["rollout_status"] == "completed",
                "applied": True,
                **rollout,
                "deployment": deployment,
                "namespace": namespace,
                "restored_backup_id": backup_id,
                "recovery_backup_id": (
                    recovery_backup["id"]
                ),
                "apply_output": (
                    apply_result.stdout.strip()
                ),

            }

        finally:
            if os.path.exists(
                yaml_path
            ):
                os.remove(
                    yaml_path
                )

    def _create_backup(
        self,
        namespace: str,
        deployment: str,
        yaml_content: str,
        reason: str,
    ) -> dict[str, Any]:
        """Create a local Deployment YAML backup."""

        directory = self._backup_directory(
            namespace,
            deployment,
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        now = datetime.now(
            timezone.utc
        )

        backup_id = now.strftime(
            "%Y%m%dT%H%M%S%fZ"
        )

        try:
            context = (
                self.client
                .current_context()
                .stdout
                .strip()
            )

        except Exception:
            context = ""

        metadata = {
            "id": backup_id,
            "context": context,
            "namespace": namespace,
            "deployment": deployment,
            "created_at": now.isoformat(),
            "reason": reason,
        }

        yaml_path = (
            directory
            / f"{backup_id}.yaml"
        )

        metadata_path = (
            directory
            / f"{backup_id}.json"
        )

        yaml_path.write_text(
            yaml_content,
            encoding="utf-8",
        )

        metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
            ),
            encoding="utf-8",
        )

        return metadata

    @staticmethod
    def _backup_directory(
        namespace: str,
        deployment: str,
    ) -> Path:
        """Return the backup directory for a Deployment."""

        return (
            BACKUP_ROOT
            / namespace
            / deployment
        )

    @staticmethod
    def _validate_backup_id(
        backup_id: str,
    ) -> None:
        """Validate backup ID before using it as a filename."""

        if not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", backup_id):
            raise ValueError("Invalid backup ID.")
