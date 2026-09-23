from __future__ import annotations

from typing import Any


class DiagnosticCorrelationService:
    """
    Correlates multiple diagnostic issues into a higher-level
    deterministic root cause analysis.

    This service does not execute kubectl commands and does not use AI.
    """

    def analyze(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not issues:
            return {
                "root_cause": None,
                "confidence": 0,
                "summary": (
                    "No known failure patterns were detected."
                ),
                "evidence": [],
                "related_issues": [],
                "recommended_actions": [],
            }

        correlation = (
            self._find_primary_cause(
                issues
            )
        )

        if correlation is None:
            return {
                "root_cause": None,
                "confidence": 25,
                "summary": (
                    "Diagnostic issues were detected, "
                    "but a deterministic root cause could "
                    "not be identified."
                ),
                "evidence": self._collect_evidence(
                    issues
                ),
                "related_issues": issues,
                "recommended_actions": [
                    "Review the pod diagnostics.",
                    "Check Kubernetes events.",
                    "Inspect current and previous container logs.",
                ],
            }

        return correlation

    def _find_primary_cause(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        rules = [
            self._crash_loop_rule,
            self._image_pull_rule,
            self._oom_rule,
            self._configuration_rule,
            self._scheduling_rule,
            self._volume_rule,
            self._dns_rule,
            self._authentication_rule,
            self._connection_rule,
            self._http_5xx_rule,
        ]

        matches: list[
            dict[str, Any]
        ] = []

        for rule in rules:
            result = rule(
                issues
            )

            if result:
                matches.append(
                    result
                )

        if not matches:
            return None

        matches.sort(
            key=lambda item: (
                item.get(
                    "confidence",
                    0,
                ),
                item.get(
                    "priority",
                    0,
                ),
            ),
            reverse=True,
        )

        best = matches[0]

        best.pop(
            "priority",
            None,
        )

        return best

    def _crash_loop_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if "crashloopbackoff"
            in self._issue_text(
                issue
            )
        ]

        if not matches:
            return None

        related = self._related_container_issues(
            issues,
            matches,
        )

        confidence = (
            self._calculate_confidence(
                base=75,
                related=related,
            )
        )

        return {
            "priority": 100,
            "root_cause": (
                "Application is repeatedly crashing"
            ),
            "confidence": confidence,
            "summary": (
                "The container is in CrashLoopBackOff, "
                "indicating repeated application failures "
                "during startup or runtime."
            ),
            "evidence": self._collect_evidence(
                related
            ),
            "related_issues": related,
            "recommended_actions": [
                "Inspect previous container logs for the original crash.",
                "Verify environment variables and configuration.",
                "Check Secrets and ConfigMaps required by the application.",
                "Verify the container command and startup arguments.",
                "Check resource limits and application memory usage.",
            ],
        }

    def _image_pull_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "imagepullbackoff"
                in self._issue_text(
                    issue
                )
                or "errimagepull"
                in self._issue_text(
                    issue
                )
                or "invalid image name"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=90,
                related=matches,
            )
        )

        return {
            "priority": 95,
            "root_cause": (
                "Container image cannot be pulled"
            ),
            "confidence": confidence,
            "summary": (
                "Kubernetes cannot retrieve or validate "
                "the configured container image."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Verify the container image name.",
                "Verify the image tag.",
                "Confirm the image exists in the registry.",
                "Check imagePullSecrets for private registries.",
                "Verify registry connectivity and authentication.",
            ],
        }

    def _oom_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "oomkilled"
                in self._issue_text(
                    issue
                )
                or "out of memory"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=90,
                related=matches,
            )
        )

        return {
            "priority": 98,
            "root_cause": (
                "Container exceeded available memory"
            ),
            "confidence": confidence,
            "summary": (
                "The container was terminated because "
                "memory usage exceeded available limits "
                "or node capacity."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Review the container memory limit.",
                "Review the container memory request.",
                "Inspect the application for memory leaks.",
                "Check for unexpected memory spikes.",
                "Verify available memory on the Kubernetes node.",
            ],
        }

    def _configuration_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "createcontainerconfigerror"
                in self._issue_text(
                    issue
                )
                or "configuration error"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=85,
                related=matches,
            )
        )

        return {
            "priority": 90,
            "root_cause": (
                "Container configuration is invalid or incomplete"
            ),
            "confidence": confidence,
            "summary": (
                "Kubernetes could not create the container "
                "because required configuration is missing "
                "or invalid."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Verify required ConfigMaps exist.",
                "Verify required Secrets exist.",
                "Check environment variable configuration.",
                "Check volume mounts and volume references.",
                "Verify referenced Kubernetes resources are in the correct namespace.",
            ],
        }

    def _scheduling_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "failedscheduling"
                in self._issue_text(
                    issue
                )
                or "cannot be scheduled"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=90,
                related=matches,
            )
        )

        return {
            "priority": 88,
            "root_cause": (
                "Pod cannot be scheduled onto a Kubernetes node"
            ),
            "confidence": confidence,
            "summary": (
                "Kubernetes could not find a suitable node "
                "for the pod."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Check node CPU and memory availability.",
                "Review node selectors.",
                "Review pod affinity and anti-affinity rules.",
                "Check node taints and pod tolerations.",
                "Verify requested resources are available in the cluster.",
            ],
        }

    def _volume_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "failedmount"
                in self._issue_text(
                    issue
                )
                or "failed to mount"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=90,
                related=matches,
            )
        )

        return {
            "priority": 89,
            "root_cause": (
                "Required storage or volume could not be mounted"
            ),
            "confidence": confidence,
            "summary": (
                "The pod cannot start because Kubernetes "
                "failed to attach or mount a required volume."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Check PersistentVolumeClaim status.",
                "Check PersistentVolume status.",
                "Verify the referenced Secret or ConfigMap exists.",
                "Review volume configuration in the workload specification.",
                "Check the storage provider and CSI driver status.",
            ],
        }

    def _dns_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "dns resolution"
                in self._issue_text(
                    issue
                )
                or "name or service not known"
                in self._issue_text(
                    issue
                )
                or "temporary failure in name resolution"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=75,
                related=matches,
            )
        )

        return {
            "priority": 75,
            "root_cause": (
                "Application cannot resolve a required hostname"
            ),
            "confidence": confidence,
            "summary": (
                "Application logs indicate a DNS or hostname "
                "resolution failure."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Verify the configured hostname.",
                "Check Kubernetes Service names.",
                "Verify the target namespace.",
                "Check CoreDNS health.",
                "Test DNS resolution from inside the pod.",
            ],
        }

    def _authentication_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "authentication failure"
                in self._issue_text(
                    issue
                )
                or "authentication failed"
                in self._issue_text(
                    issue
                )
                or "http authentication failures"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=70,
                related=matches,
            )
        )

        return {
            "priority": 70,
            "root_cause": (
                "Application authentication is failing"
            ),
            "confidence": confidence,
            "summary": (
                "Collected diagnostics indicate failed "
                "authentication attempts."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Verify configured credentials.",
                "Check Kubernetes Secret values.",
                "Verify authentication tokens are valid.",
                "Check token expiration.",
                "Verify authentication endpoint configuration.",
            ],
        }

    def _connection_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "connection refused"
                in self._issue_text(
                    issue
                )
                or "connection timeout"
                in self._issue_text(
                    issue
                )
                or "connection reset"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=70,
                related=matches,
            )
        )

        return {
            "priority": 72,
            "root_cause": (
                "Application dependency connection is failing"
            ),
            "confidence": confidence,
            "summary": (
                "Application logs indicate failures when "
                "connecting to an external dependency."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Verify the target service is running.",
                "Check the configured host and port.",
                "Verify Kubernetes Service endpoints.",
                "Check NetworkPolicies.",
                "Test connectivity from inside the pod.",
            ],
        }

    def _http_5xx_rule(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            issue
            for issue in issues
            if (
                "http internal server errors"
                in self._issue_text(
                    issue
                )
                or "http bad gateway"
                in self._issue_text(
                    issue
                )
                or "http service unavailable"
                in self._issue_text(
                    issue
                )
                or "http gateway timeout"
                in self._issue_text(
                    issue
                )
            )
        ]

        if not matches:
            return None

        confidence = (
            self._calculate_confidence(
                base=65,
                related=matches,
            )
        )

        return {
            "priority": 65,
            "root_cause": (
                "Application or upstream dependency is returning server errors"
            ),
            "confidence": confidence,
            "summary": (
                "Application logs contain HTTP 5xx responses, "
                "indicating an application or upstream service failure."
            ),
            "evidence": self._collect_evidence(
                matches
            ),
            "related_issues": matches,
            "recommended_actions": [
                "Inspect application error logs.",
                "Check upstream service health.",
                "Verify backend service endpoints.",
                "Check dependency availability.",
                "Review recent application configuration changes.",
            ],
        }

    def _related_container_issues(
        self,
        issues: list[dict[str, Any]],
        matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        containers = {
            issue.get("container")
            for issue in matches
            if issue.get("container")
        }

        if not containers:
            return matches

        related: list[
            dict[str, Any]
        ] = []

        for issue in issues:
            container = (
                issue.get("container")
            )

            if (
                container in containers
                or issue in matches
            ):
                related.append(
                    issue
                )

        return related

    def _calculate_confidence(
        self,
        base: int,
        related: list[dict[str, Any]],
    ) -> int:
        additional = max(
            len(related) - 1,
            0,
        ) * 5

        return min(
            base + additional,
            100,
        )

    def _collect_evidence(
        self,
        issues: list[dict[str, Any]],
    ) -> list[str]:
        evidence: list[str] = []

        for issue in issues:
            title = (
                issue.get("title")
                or "Diagnostic issue"
            )

            issue_evidence = (
                issue.get("evidence")
                or []
            )

            if isinstance(
                issue_evidence,
                str,
            ):
                issue_evidence = [
                    issue_evidence
                ]

            if not issue_evidence:
                evidence.append(
                    title
                )

                continue

            for item in issue_evidence:
                evidence.append(
                    f"{title}: {item}"
                )

        return evidence

    def _issue_text(
        self,
        issue: dict[str, Any],
    ) -> str:
        parts = [
            str(
                issue.get(
                    "title",
                    "",
                )
            ),
            str(
                issue.get(
                    "category",
                    "",
                )
            ),
            str(
                issue.get(
                    "message",
                    "",
                )
            ),
            str(
                issue.get(
                    "description",
                    "",
                )
            ),
        ]

        evidence = (
            issue.get("evidence")
            or []
        )

        if isinstance(
            evidence,
            list,
        ):
            parts.extend(
                str(item)
                for item in evidence
            )

        else:
            parts.append(
                str(evidence)
            )

        return " ".join(
            parts
        ).lower()