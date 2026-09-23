from __future__ import annotations

from typing import Any

from app.kubernetes.services.investigation.timeout_evidence import is_timeout_failure


class PodRootCauseService:
    """
    Deterministic root-cause correlation engine.

    Input:
        - pod/cluster investigation evidence
        - deterministic diagnostic issues

    Output:
        - correlated root causes
        - confidence score
        - supporting evidence
        - recommended actions

    This service:
        - does not execute kubectl commands
        - does not use AI
        - does not invent evidence
        - separates symptoms from underlying causes
        - removes redundant symptom-level root causes
        - removes secondary causes when a direct blocker is identified
        - ranks more specific causes above generic causes
    """

    def analyze(
        self,
        investigation: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> dict[str, Any]:
        all_issues = diagnostics.get("issues") or []
        scoped = {}
        for issue in all_issues:
            if isinstance(issue, dict) and issue.get("pod"):
                scoped.setdefault(issue["pod"], []).append(issue)
        if scoped:
            causes = []
            for pod, group in scoped.items():
                result = self.analyze(investigation, {"issues": [dict(i, pod=None) for i in group]})
                causes.extend(dict(c, pod=pod) for c in result["root_causes"])
            unscoped = [i for i in all_issues if isinstance(i, dict) and not i.get("pod")]
            causes.extend(self.analyze(investigation, {"issues": unscoped})["root_causes"])
            causes = self._rank(causes)
            return {"root_cause_count": len(causes), "root_causes": causes}
        issues = [i for i in all_issues if isinstance(i, dict) and not i.get("verified_finding")]

        if not isinstance(issues, list):
            issues = []

        root_causes: list[dict[str, Any]] = []
        for issue in all_issues:
            if not isinstance(issue, dict) or not issue.get("verified_finding"):
                continue
            cause = self._root_cause(title=issue["title"], category=issue["category"],
                severity=issue["severity"], confidence=issue["confidence"],
                description=" ".join(issue["evidence"]), evidence=issue["evidence"],
                recommended_actions=issue["recommended_actions"])
            cause.update({k: issue[k] for k in ("service", "deployment", "pvc") if k in issue})
            root_causes.append(cause)
        for issue in issues:
            if issue.get("category") == "node" or (issue.get("category") == "resources" and "utilization" in self._title(issue).lower()):
                root_causes.append(self._root_cause(title=self._title(issue), category="resources" if "pressure" in self._title(issue).lower() or issue.get("category") == "resources" else "node",
                    severity=issue.get("severity", "warning"), confidence=90,
                    description="The collected node condition or utilization reports this resource state; application causality requires correlation.",
                    evidence=self._evidence([issue]), recommended_actions=["Review the affected node and workload resource usage.", "Inspect requests, limits and capacity before changing allocation."]))

        # =========================================================
        # SPECIFIC / HIGH-VALUE DETECTORS FIRST
        # =========================================================

        self._detect_network_failure(issues, root_causes)

        self._detect_oom(
            issues,
            root_causes,
        )

        self._detect_image_pull(
            issues,
            root_causes,
        )

        self._detect_scheduling(
            issues,
            root_causes,
        )

        self._detect_mount_failure(
            issues,
            root_causes,
        )

        self._detect_probe_failure(
            issues,
            root_causes,
        )

        self._detect_configuration_failure(
            issues,
            root_causes,
        )

        self._detect_dns(
            issues,
            root_causes,
        )

        self._detect_timeout(
            issues,
            root_causes,
        )

        self._detect_connection_refused(
            issues,
            root_causes,
        )

        self._detect_service_failure(
            issues,
            root_causes,
        )

        self._detect_authentication(
            investigation,
            issues,
            root_causes,
        )

        self._detect_authorization(
            issues,
            root_causes,
        )

        self._detect_application_failure(
            issues,
            root_causes,
        )

        self._detect_build_failure(
            issues,
            root_causes,
        )

        # =========================================================
        # GENERIC SYMPTOM DETECTOR
        # =========================================================

        self._detect_crash_loop(
            issues,
            root_causes,
        )

        # =========================================================
        # CLEANUP
        # =========================================================

        root_causes = self._deduplicate(
            root_causes,
        )

        root_causes = self._remove_redundant_symptom_root_causes(
            root_causes,
        )

        root_causes = self._remove_secondary_causes_for_image_failure(
            root_causes,
        )

        root_causes = self._remove_secondary_causes_for_configuration_failure(
            root_causes,
        )

        root_causes = self._rank(
            root_causes,
        )

        return {
            "root_cause_count": len(root_causes),
            "root_causes": root_causes,
        }

    # =========================================================
    # CRASH LOOP
    # =========================================================

    def _detect_crash_loop(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        crash = self._find(
            issues,
            title_contains="CrashLoopBackOff",
        )

        restart = self._find_category(
            issues,
            "restarts",
        )

        if not crash:
            return

        specific_failure_categories = {
            str(
                cause.get("category") or ""
            ).lower()
            for cause in root_causes
            if isinstance(cause, dict)
        }

        if specific_failure_categories.intersection(
            {
                "build",
                "configuration",
                "image",
                "resources",
                "scheduling",
                "storage",
                "health",
                "network",
                "service",
                "authentication",
                "authorization",
            }
        ):
            return

        fatal = [
            issue
            for issue in issues
            if issue.get("category")
            in {
                "logs",
                "build",
            }
            and (
                "fatal"
                in self._issue_text(issue).lower()
                or "exception"
                in self._issue_text(issue).lower()
                or "compilation"
                in self._issue_text(issue).lower()
                or "build failure"
                in self._issue_text(issue).lower()
            )
        ]

        confidence = 70

        if restart:
            confidence += 10

        if fatal:
            confidence += 10

        root_causes.append(
            self._root_cause(
                title="Application is repeatedly crashing",
                category="application",
                severity="critical",
                confidence=min(
                    confidence,
                    95,
                ),
                description=(
                    "The container is repeatedly crashing "
                    "and Kubernetes is attempting to restart it."
                ),
                evidence=self._evidence(
                    crash + restart + fatal
                ),
                recommended_actions=[
                    "Inspect previous container logs.",
                    "Check the application startup command.",
                    "Verify environment variables and Secrets.",
                    "Check for missing dependencies.",
                    "Review recent application configuration changes.",
                ],
            )
        )

    # =========================================================
    # OOM
    # =========================================================

    def _detect_oom(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        oom = self._find(
            issues,
            title_contains="OOMKilled",
        )

        memory = [
            issue
            for issue in issues
            if issue.get("category")
            in {
                "logs",
                "resources",
            }
            and "memory"
            in self._issue_text(issue).lower()
        ]

        if not oom:
            application_memory = [i for i in memory if self._title(i) == "Out of memory error detected"]
            if application_memory:
                root_causes.append(self._root_cause(title="Application reported memory exhaustion", category="resources", severity="critical", confidence=80,
                    description="Application logs report memory exhaustion; Kubernetes OOMKilled has not been established.", evidence=self._evidence(application_memory),
                    recommended_actions=["Review application memory usage and logs.", "Check limits and node memory pressure."]))
            return

        termination_evidence = " ".join(self._evidence(oom))
        historical_only = (
            "last_state.terminated.reason=OOMKilled" in termination_evidence
            and "state.terminated.reason=OOMKilled" not in
                termination_evidence.replace("last_state.terminated.reason=OOMKilled", "")
        )

        confidence = 85

        if memory:
            confidence += 10

        root_causes.append(
            self._root_cause(
                title=("Previous container OOM kill recorded" if historical_only else "Container exceeded available memory"),
                category="resources",
                severity="critical",
                confidence=min(
                    confidence,
                    98,
                ),
                description=(
                    ("A previous container termination was recorded as OOMKilled. "
                     "This historical record does not establish a current outage or ongoing memory exhaustion. "
                     if historical_only else
                     "Kubernetes recorded an out-of-memory kill in the current termination state. ")
                    + "The reason alone does not identify a memory leak or distinguish a container limit from node exhaustion."
                ),
                evidence=self._evidence(
                    oom + memory
                ),
                recommended_actions=[
                    "Check the container memory limit.",
                    "Check the container memory request.",
                    "Inspect application memory usage.",
                    "Investigate possible memory leaks.",
                    "Increase memory limits if justified.",
                    "Check node memory pressure.",
                ],
            )
        )

    # =========================================================
    # IMAGE
    # =========================================================

    def _detect_image_pull(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        image_issues = [
            issue
            for issue in issues
            if issue.get("category") == "image"
        ]

        if not image_issues:
            return

        combined_evidence = " ".join(
            self._evidence(
                image_issues
            )
        ).lower()

        if (
            "not found"
            in combined_evidence
            or "notfound"
            in combined_evidence
        ):
            root_causes.append(
                self._root_cause(
                    title=(
                        "Container image or image tag was not found"
                    ),
                    category="image",
                    severity="critical",
                    confidence=95,
                    description=(
                        "Kubernetes attempted to pull the configured "
                        "container image, but the referenced image or "
                        "image tag was not found."
                    ),
                    evidence=self._evidence(
                        image_issues
                    ),
                    recommended_actions=[
                        "Verify the configured image name.",
                        "Verify the configured image tag.",
                        "Confirm the image exists in the configured registry.",
                        "Verify the workload references the intended image.",
                        "Redeploy after correcting the image reference.",
                    ],
                )
            )

            return

        root_causes.append(
            self._root_cause(
                title="Container image cannot be pulled",
                category="image",
                severity="critical",
                confidence=90,
                description=(
                    "Kubernetes cannot download or validate "
                    "the container image required by the workload."
                ),
                evidence=self._evidence(
                    image_issues
                ),
                recommended_actions=[
                    "Verify the image name.",
                    "Verify the image tag.",
                    "Confirm the image exists in the registry.",
                    "Check imagePullSecrets.",
                    "Verify registry credentials.",
                    "Check registry connectivity.",
                ],
            )
        )

    # =========================================================
    # SCHEDULING
    # =========================================================

    def _detect_scheduling(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        scheduling = [
            issue
            for issue in issues
            if (
                issue.get("category") == "scheduling"
                or "failedscheduling"
                in self._issue_text(issue).lower()
                or "cannot be scheduled"
                in self._issue_text(issue).lower()
            )
        ]

        pending = [
            issue
            for issue in issues
            if "pending"
            in self._issue_text(issue).lower()
        ]

        if not scheduling:
            return

        confidence = 85 if scheduling else 65

        root_causes.append(
            self._root_cause(
                title="Kubernetes scheduling failure",
                category="scheduling",
                severity="critical",
                confidence=confidence,
                description=(
                    "The pod cannot be scheduled because "
                    "one or more cluster scheduling requirements "
                    "are not satisfied."
                ),
                evidence=self._evidence(
                    scheduling + pending
                ),
                recommended_actions=[
                    "Check available node CPU and memory.",
                    "Check pod resource requests.",
                    "Check node selectors.",
                    "Check node taints and tolerations.",
                    "Check affinity and anti-affinity rules.",
                    "Review FailedScheduling events.",
                ],
            )
        )

    # =========================================================
    # VOLUME / MOUNT
    # =========================================================

    def _detect_mount_failure(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        mount = [
            issue
            for issue in issues
            if (
                issue.get("category") == "storage"
                or "mount"
                in self._issue_text(issue).lower()
                or "failedattachvolume" in self._issue_text(issue).lower()
            )
        ]

        if not mount:
            return

        root_causes.append(
            self._root_cause(
                title="Volume or configuration mount failure",
                category="storage",
                severity="critical",
                confidence=88,
                description=(
                    "Kubernetes reported that a required volume, "
                    "Secret, ConfigMap, or storage resource "
                    "could not be mounted."
                ),
                evidence=self._evidence(
                    mount
                ),
                recommended_actions=[
                    "Check PersistentVolumeClaim status.",
                    "Check PersistentVolume status.",
                    "Verify referenced ConfigMaps exist.",
                    "Verify referenced Secrets exist.",
                    "Check volume names and mount paths.",
                    "Review storage provider events.",
                ],
            )
        )

    # =========================================================
    # PROBES
    # =========================================================

    def _detect_probe_failure(self, issues, root_causes) -> None:
        probe = [i for i in issues if i.get("category") == "probe" or "probe failed" in self._issue_text(i).lower() or "health check" in self._issue_text(i).lower()]
        for kind in ("readiness", "liveness", "startup", "unspecified"):
            matching = [i for i in probe if (kind in self._issue_text(i).lower() if kind != "unspecified" else not any(k in self._issue_text(i).lower() for k in ("readiness", "liveness", "startup")))]
            if not matching:
                continue
            label = kind.title() if kind != "unspecified" else "Container health"
            root_causes.append(self._root_cause(title=f"{label} probe failure", category="health", severity="high", confidence=88,
                description="Collected health-check evidence reports probe failure. This may be a symptom of an application startup or dependency failure.",
                evidence=self._evidence(matching), recommended_actions=["Review the probe failure message.", "Verify the probe port, path and timing against application behavior.", "Review container logs before changing thresholds."]))

    # =========================================================
    # CONFIGURATION
    # =========================================================

    def _detect_configuration_failure(self, issues, root_causes) -> None:
        configuration = [i for i in issues if i.get("category") == "configuration"]
        parsing = [i for i in configuration if "parsing" in self._title(i).lower() or "yaml" in self._issue_text(i).lower()]
        other = [i for i in configuration if i not in parsing]
        if parsing:
            root_causes.append(self._root_cause(title="Application configuration parsing failure", category="configuration", severity="critical", confidence=95,
                description="The application reports a configuration parsing or syntax failure.", evidence=self._evidence(parsing),
                recommended_actions=["Review the configuration file at the reported line.", "Correct and validate the configuration syntax.", "Restart or redeploy after correcting the configuration.", "Verify the application starts successfully."]))
        if other:
            root_causes.append(self._root_cause(title="Container configuration failure", category="configuration", severity="critical", confidence=90,
                description="Kubernetes reported a container configuration failure. Review the exact message to identify the missing or invalid resource.", evidence=self._evidence(other),
                recommended_actions=["Review referenced Secrets and ConfigMaps.", "Check the container configuration and reported event message."]))

    # =========================================================
    # DNS
    # =========================================================

    def _detect_dns(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        dns = [
            issue
            for issue in issues
            if (
                "dns"
                in self._issue_text(issue).lower()
                or "resolution"
                in self._issue_text(issue).lower()
            )
        ]

        if not dns:
            return

        root_causes.append(
            self._root_cause(
                title="DNS or service discovery failure",
                category="network",
                severity="warning",
                confidence=85,
                description=(
                    "Application evidence indicates that "
                    "a hostname or Kubernetes service name "
                    "cannot be resolved."
                ),
                evidence=self._evidence(
                    dns
                ),
                recommended_actions=[
                    "Verify the target hostname.",
                    "Check the Kubernetes Service name.",
                    "Check the Service namespace.",
                    "Check CoreDNS health.",
                    "Test DNS resolution from the affected pod.",
                    "Check cluster networking.",
                ],
            )
        )

    # =========================================================
    # TIMEOUT
    # =========================================================

    def _detect_timeout(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        timeout = []
        for issue in issues:
            if self._is_probe_issue(issue):
                continue
            category = issue.get("category")
            is_gateway = category == "http" and "gateway timeout" in self._title(issue).lower()
            if category not in {"http", "network", "logs"}:
                continue
            evidence = self._evidence([issue])
            matched = evidence if is_gateway else [line for line in evidence if is_timeout_failure(line)]
            if matched:
                timeout.append({**issue, "evidence": matched})

        if not timeout:
            return

        confidence = 65

        if any(issue.get("category") == "http" and
               "gateway timeout" in self._title(issue).lower() for issue in timeout):
            confidence = 80

        root_causes.append(
            self._root_cause(
                title="Upstream dependency or network timeout",
                category="network",
                severity="warning",
                confidence=confidence,
                description=(
                    "Collected evidence reports a timeout failure. The affected operation and underlying cause must be verified from the message; a timeout alone does not establish a network or dependency fault."
                ),
                evidence=self._evidence(
                    timeout
                ),
                recommended_actions=[
                    "Identify the dependency receiving the request.",
                    "Check upstream service health.",
                    "Check Service endpoints.",
                    "Review network latency.",
                    "Review application and proxy timeout settings.",
                ],
            )
        )

    # =========================================================
    # SERVICE / GATEWAY
    # =========================================================

    def _detect_service_failure(self, issues, root_causes) -> None:
        service = [i for i in issues if i.get("category") == "http" and any(t in self._title(i).lower() for t in ("bad gateway", "service unavailable"))]
        if service:
            root_causes.append(self._root_cause(title="Upstream application or service is unavailable", category="service", severity="critical", confidence=85,
                description="Gateway or service-level HTTP failures indicate an unhealthy or unreachable upstream.", evidence=self._evidence(service),
                recommended_actions=["Check the upstream Service and endpoints.", "Inspect selected pods and gateway configuration."]))

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _detect_authentication(
        self,
        investigation: dict[str, Any],
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        auth = [issue for issue in issues
                if issue.get("category") == "authentication"
                or (issue.get("category") == "http"
                    and "401" in " ".join(self._evidence([issue])))]
        if not auth:
            return
        explicit = any(issue.get("category") == "authentication" for issue in auth)
        root_causes.append(self._root_cause(
            title=("Application authentication failure" if explicit else "HTTP 401 responses observed"),
            category="authentication", severity=("warning" if explicit else "info"),
            confidence=(75 if explicit else 50),
            description=("Application logs explicitly report authentication failure; the underlying cause is not established."
                if explicit else
                "Requests received HTTP 401 responses. These may be expected authentication challenges or rejected requests; they do not establish broken credentials or an application outage."),
            evidence=self._evidence(auth),
            recommended_actions=[
                "Check whether affected requests were expected to include valid credentials.",
                "Correlate rejected requests with successful authenticated requests and their timestamps.",
                "Investigate authentication configuration only if legitimate requests are failing.",
            ],
        ))

    # =========================================================
    # AUTHORIZATION
    # =========================================================

    def _detect_authorization(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        authorization = [
            issue
            for issue in issues
            if not self._is_probe_issue(issue) and (
                "authorization"
                in self._issue_text(issue).lower()
                or "permission"
                in self._issue_text(issue).lower()
                or "403"
                in " ".join(
                    self._evidence([issue])
                )
            )
        ]

        if not authorization:
            return

        root_causes.append(
            self._root_cause(
                title="Permission or authorization failure",
                category="authorization",
                severity="warning",
                confidence=85,
                description=(
                    "The application is encountering "
                    "authorization or permission failures."
                ),
                evidence=self._evidence(
                    authorization
                ),
                recommended_actions=[
                    "Check application permissions.",
                    "Check Kubernetes RBAC configuration.",
                    "Verify ServiceAccount permissions.",
                    "Check filesystem ownership and permissions.",
                    "Review securityContext configuration.",
                ],
            )
        )

    # =========================================================
    # APPLICATION
    # =========================================================

    def _detect_application_failure(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        application = [
            issue
            for issue in issues
            if (
                issue.get("category") == "logs"
                and (
                    "fatal"
                    in self._issue_text(issue).lower()
                    or "exception"
                    in self._issue_text(issue).lower()
                    or "internal server"
                    in self._issue_text(issue).lower()
                    or "500"
                    in " ".join(
                        self._evidence([issue])
                    )
                )
            )
        ]

        if not application:
            return

        root_causes.append(
            self._root_cause(
                title="Application runtime failure",
                category="application",
                severity="critical",
                confidence=82,
                description=(
                    "The collected evidence indicates an "
                    "application runtime error or backend failure."
                ),
                evidence=self._evidence(
                    application
                ),
                recommended_actions=[
                    "Review application stack traces.",
                    "Check recent application deployments.",
                    "Verify application configuration.",
                    "Check required environment variables.",
                    "Check dependent services.",
                    "Compare with the previous working version.",
                ],
            )
        )

    # =========================================================
    # BUILD FAILURE
    # =========================================================

    def _detect_build_failure(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        build_issues = [
            issue
            for issue in issues
            if issue.get("category") == "build"
        ]

        if not build_issues:
            return

        root_causes.append(
            self._root_cause(
                title="Application build or compilation failure",
                category="build",
                severity="critical",
                confidence=92,
                description=(
                    "The application container is failing because "
                    "its build or compilation process is failing."
                ),
                evidence=self._evidence(
                    build_issues
                ),
                recommended_actions=[
                    "Review the compiler error in the container logs.",
                    "Verify the required dependency and type declarations.",
                    "Check package.json dependency versions.",
                    "Rebuild the application image after correcting the build error.",
                    "Verify the rebuilt image is deployed.",
                ],
            )
        )

    # =========================================================
    # REDUNDANT SYMPTOM REMOVAL
    # =========================================================

    @staticmethod
    def _remove_redundant_symptom_root_causes(
        root_causes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        categories = {
            str(
                item.get("category") or ""
            ).lower()
            for item in root_causes
            if isinstance(item, dict)
        }

        specific_categories = categories.intersection(
            {
                "build",
                "configuration",
                "image",
                "resources",
                "scheduling",
                "storage",
                "health",
                "network",
                "service",
                "authentication",
                "authorization",
            }
        )

        if not specific_categories:
            return root_causes

        filtered: list[dict[str, Any]] = []

        for item in root_causes:
            if not isinstance(item, dict):
                continue

            category = str(
                item.get("category") or ""
            ).lower()

            title = str(
                item.get("title") or ""
            ).lower()

            is_generic_application_crash = (
                category == "application"
                and any(
                    phrase in title
                    for phrase in (
                        "repeatedly crashing",
                        "crash loop",
                        "crashloopbackoff",
                    )
                )
            )

            if (
                is_generic_application_crash
                and specific_categories
            ):
                continue

            filtered.append(item)

        return filtered

    # =========================================================
    # IMAGE FAILURE SECONDARY-CAUSE REMOVAL
    # =========================================================

    @staticmethod
    def _remove_secondary_causes_for_image_failure(
        root_causes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        has_image_not_found = any(
            isinstance(root_cause, dict)
            and str(
                root_cause.get("category") or ""
            ).lower() == "image"
            and (
                "not found"
                in str(
                    root_cause.get("title") or ""
                ).lower()
                or "image tag was not found"
                in str(
                    root_cause.get("title") or ""
                ).lower()
            )
            for root_cause in root_causes
        )

        if not has_image_not_found:
            return root_causes

        filtered: list[dict[str, Any]] = []

        for root_cause in root_causes:
            if not isinstance(root_cause, dict):
                continue

            category = str(
                root_cause.get("category") or ""
            ).lower()

            if category in {
                "application",
                "network",
            }:
                continue

            filtered.append(
                root_cause
            )

        return filtered

    # =========================================================
    # CONFIGURATION FAILURE SECONDARY-CAUSE REMOVAL
    # =========================================================

    @staticmethod
    def _remove_secondary_causes_for_configuration_failure(
        root_causes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        When a direct configuration parsing failure exists,
        remove root causes that merely describe downstream
        application availability symptoms.

        Example:

            configuration parsing failure
            +
            local application endpoint unavailable
            +
            application repeatedly crashing

        becomes:

            configuration parsing failure
        """

        has_configuration_failure = any(
            isinstance(root_cause, dict)
            and str(
                root_cause.get("category") or ""
            ).lower() == "configuration"
            for root_cause in root_causes
        )

        if not has_configuration_failure:
            return root_causes

        filtered: list[dict[str, Any]] = []

        for root_cause in root_causes:
            if not isinstance(
                root_cause,
                dict,
            ):
                continue

            category = str(
                root_cause.get("category") or ""
            ).lower()

            title = str(
                root_cause.get("title") or ""
            ).lower()

            if (
                category == "application"
                and (
                    "local application endpoint"
                    in title
                    or "repeatedly crashing"
                    in title
                    or "crash loop"
                    in title
                    or "crashloopbackoff"
                    in title
                )
            ):
                continue

            filtered.append(
                root_cause
            )

        return filtered

    # =========================================================
    # CONNECTION REFUSED
    # =========================================================

    def _detect_connection_refused(
        self,
        issues: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> None:
        connection_issues = [
            issue
            for issue in issues
            if not self._is_probe_issue(issue) and (
                "connection refused"
                in self._issue_text(issue).lower()
            )
        ]

        if not connection_issues:
            return

        local_connection_issues: list[
            dict[str, Any]
        ] = []

        remote_connection_issues: list[
            dict[str, Any]
        ] = []

        for issue in connection_issues:
            text = self._issue_text(
                issue
            ).lower()

            if any(
                host in text
                for host in (
                    "127.0.0.1",
                    "localhost",
                    "::1",
                )
            ):
                local_connection_issues.append(
                    issue
                )
            else:
                remote_connection_issues.append(
                    issue
                )

        # --------------------------------------------------------
        # Local / loopback connection refused
        #
        # A direct configuration failure explains this as a
        # downstream symptom, so do not promote it to a separate
        # root cause.
        # --------------------------------------------------------

        has_configuration_failure = any(
            isinstance(root_cause, dict)
            and str(
                root_cause.get("category") or ""
            ).lower() == "configuration"
            for root_cause in root_causes
        )

        if (
            local_connection_issues
            and not has_configuration_failure
        ):
            root_causes.append(
                self._root_cause(
                    title="Local application endpoint is unavailable",
                    category="application",
                    severity="high",
                    confidence=70,
                    description=(
                        "Application evidence shows a connection refused "
                        "error against a loopback endpoint. This indicates "
                        "that the endpoint was not accepting connections at "
                        "the time of the observed request, but the supplied "
                        "evidence does not establish why."
                    ),
                    evidence=self._evidence(
                        local_connection_issues
                    ),
                    recommended_actions=[
                        "Identify which container owns the local endpoint.",
                        "Check whether the target application process is running.",
                        "Review the target container logs.",
                        "Verify the target port is listening.",
                        "Check the startup and health state of the affected container.",
                    ],
                )
            )

        # --------------------------------------------------------
        # Remote connection refused
        # --------------------------------------------------------

        if remote_connection_issues:
            root_causes.append(
                self._root_cause(
                    title="Remote dependency connection refused",
                    category="network",
                    severity="warning",
                    confidence=70,
                    description=(
                        "Application evidence shows that a remote "
                        "endpoint refused a connection. The supplied "
                        "evidence does not by itself establish whether "
                        "the endpoint is a Kubernetes Service or another "
                        "dependency."
                    ),
                    evidence=self._evidence(
                        remote_connection_issues
                    ),
                    recommended_actions=[
                        "Identify the remote dependency.",
                        "Verify the remote endpoint and port.",
                        "Check the dependency health.",
                        "Check network connectivity from the affected pod.",
                        "Check Service endpoints when the dependency is a Kubernetes Service.",
                    ],
                )
            )

    @classmethod
    def _is_probe_issue(cls, issue: dict[str, Any]) -> bool:
        """Keep kubelet health checks separate from application traffic."""
        category = str(issue.get("category") or "").lower()
        if category == "probe":
            return True
        text = cls._issue_text(issue).lower()
        return category == "event" and any(
            phrase in text for phrase in
            ("readiness probe", "liveness probe", "startup probe", "health check")
        )

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _title(
        issue: dict[str, Any],
    ) -> str:
        return str(
            issue.get("title")
            or issue.get("type")
            or ""
        )

    @classmethod
    def _issue_text(
        cls,
        issue: dict[str, Any],
    ) -> str:
        parts: list[str] = [
            cls._title(issue)
        ]

        evidence = issue.get(
            "evidence"
        ) or []

        if isinstance(
            evidence,
            str,
        ):
            evidence = [
                evidence
            ]

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

        return " ".join(parts)

    @classmethod
    def _find(
        cls,
        issues: list[dict[str, Any]],
        title_contains: str,
    ) -> list[dict[str, Any]]:
        needle = title_contains.lower()

        return [
            issue
            for issue in issues
            if needle
            in cls._issue_text(issue).lower()
        ]

    @staticmethod
    def _find_category(
        issues: list[dict[str, Any]],
        category: str,
    ) -> list[dict[str, Any]]:
        return [
            issue
            for issue in issues
            if str(
                issue.get("category") or ""
            ).lower()
            == category.lower()
        ]

    @staticmethod
    def _evidence(
        issues: list[dict[str, Any]],
    ) -> list[str]:
        result: list[str] = []

        for issue in issues:
            evidence = issue.get(
                "evidence"
            ) or []

            if isinstance(
                evidence,
                str,
            ):
                evidence = [
                    evidence
                ]

            if not isinstance(
                evidence,
                list,
            ):
                evidence = [
                    str(evidence)
                ]

            for item in evidence:
                value = str(
                    item
                )

                if (
                    value
                    and value not in result
                ):
                    result.append(
                        value
                    )

        return result

    @staticmethod
    def _root_cause(
        *,
        title: str,
        category: str,
        severity: str,
        confidence: int,
        description: str,
        evidence: list[str],
        recommended_actions: list[str],
    ) -> dict[str, Any]:
        return {
            "title": title,
            "category": category,
            "severity": severity,
            "confidence": confidence,
            "description": description,
            "summary": description,
            "evidence": evidence,
            "recommended_actions": recommended_actions,
            "recommended_checks": recommended_actions.copy(),
        }

    @staticmethod
    def _deduplicate(
        root_causes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []

        seen: set[
            tuple[str, str]
        ] = set()

        for root_cause in root_causes:
            key = (
                str(
                    root_cause.get(
                        "category",
                        "",
                    )
                ).lower(),
                str(
                    root_cause.get(
                        "title",
                        "",
                    )
                ).lower(),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            unique.append(
                root_cause
            )

        return unique

    @staticmethod
    def _rank(
        root_causes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        severity_weight = {
            "critical": 4,
            "high": 3,
            "warning": 2,
            "medium": 2,
            "low": 1,
            "info": 0,
        }

        category_weight = {
            "build": 12,
            "configuration": 12,
            "image": 11,
            "resources": 11,
            "deployment": 6,
            "node": 10,
            "scheduling": 10,
            "storage": 10,
            "health": 9,
            "network": 8,
            "service": 8,
            "authentication": 7,
            "authorization": 7,
            "application": 4,
        }

        def score(
            root_cause: dict[str, Any],
        ) -> tuple[int, int, int]:
            severity = str(
                root_cause.get("severity")
                or ""
            ).lower()

            category = str(
                root_cause.get("category")
                or ""
            ).lower()

            try:
                confidence = int(
                    root_cause.get(
                        "confidence"
                    )
                    or 0
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence = 0

            return (
                severity_weight.get(
                    severity,
                    0,
                ),
                category_weight.get(
                    category,
                    0,
                ),
                confidence,
            )

        return sorted(
            root_causes,
            key=score,
            reverse=True,
        )
    def _detect_network_failure(self, issues, root_causes):
        matching = [i for i in issues if any(marker in self._issue_text(i).lower() for marker in ("failedcreatepodsandbox", "networknotready", "network route is unavailable"))]
        if matching:
            root_causes.append(self._root_cause(title="Pod networking or route failure", category="network", severity="critical", confidence=90,
                description="Collected events or logs report a network sandbox or route failure. This does not establish a NetworkPolicy cause.", evidence=self._evidence(matching),
                recommended_actions=["Inspect CNI and node networking status.", "Review the exact failed endpoint, route and event message."]))
