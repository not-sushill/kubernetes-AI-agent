from __future__ import annotations

import re
from typing import Any

from app.kubernetes.services.investigation.timeout_evidence import is_timeout_failure


class PodDiagnosticsService:
    """
    Deterministic Kubernetes diagnostic engine.

    This service analyzes already-collected investigation evidence.
    It does not execute kubectl commands.
    """

    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        raw_pods = self._unwrap_section(investigation.get("pod"))
        if isinstance(raw_pods, list):
            combined = []
            for pod in raw_pods:
                if not isinstance(pod, dict):
                    continue
                result = self.analyze({"pod": pod})
                for issue in result["issues"]:
                    issue["pod"] = pod.get("name")
                combined.extend(result["issues"])
            result = self.analyze({k: v for k, v in investigation.items() if k != "pod"})
            combined.extend(result["issues"])
            combined = self._deduplicate(combined)
            return {"issue_count": len(combined), "issues": combined}
        raw_logs = self._unwrap_section(investigation.get("logs"))
        if isinstance(raw_logs, dict) and isinstance(raw_logs.get("pods"), dict):
            combined = []
            for name, logs in raw_logs["pods"].items():
                result = self.analyze({"logs": logs})
                for issue in result["issues"]:
                    issue["pod"] = name
                combined.extend(result["issues"])
            result = self.analyze({k: v for k, v in investigation.items() if k != "logs"})
            combined.extend(result["issues"])
            combined = self._deduplicate(combined)
            return {"issue_count": len(combined), "issues": combined}
        issues: list[dict[str, Any]] = []
        pod = self._unwrap_section(investigation.get("pod"))
        events = self._unwrap_section(investigation.get("events"))
        logs = self._unwrap_section(investigation.get("logs"))
        nodes = self._unwrap_section(investigation.get("node"))
        metrics = self._unwrap_section(investigation.get("metrics"))

        self._detect_pod_status(pod, issues)
        self._detect_container_issues(pod, issues)
        self._detect_init_container_issues(pod, issues)
        self._detect_restart_issues(pod, issues)
        self._detect_unhealthy_pod_summaries(pod, issues)
        self._detect_events(events, issues)
        self._detect_log_patterns(logs, issues)
        self._detect_previous_log_patterns(logs, issues)
        self._detect_http_errors(logs, issues)
        self._detect_node_conditions(nodes, issues)
        self._detect_node_metrics(metrics, issues)

        issues = self._deduplicate(issues)
        return {"issue_count": len(issues), "issues": issues}

    # =========================================================
    # SECTION HANDLING
    # =========================================================

    @staticmethod
    def _unwrap_section(section: Any) -> Any:
        if not isinstance(section, dict):
            return section
        if section.get("status") in {"collected", "failed", "skipped"}:
            return section.get("data") if section.get("status") == "collected" else None
        return section

    # =========================================================
    # POD STATUS
    # =========================================================

    def _detect_pod_status(
        self, pod: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(pod, dict):
            return

        status = str(pod.get("status") or "")
        if status == "Pending":
            issues.append(self._issue(
                severity="warning",
                category="pod_status",
                title="Pod is in Pending state",
                evidence=["The pod phase is Pending."],
                possible_causes=[
                    "Insufficient cluster resources",
                    "Node selector does not match any node",
                    "Unsatisfied pod affinity rules",
                    "Persistent volume is not available",
                    "Image pull has not completed",
                ],
            ))
        elif status == "Failed":
            issues.append(self._issue(
                severity="critical",
                category="pod_status",
                title="Pod is in Failed state",
                evidence=["The pod phase is Failed."],
                possible_causes=[
                    "Container terminated unexpectedly",
                    "Application startup failed",
                    "Pod exceeded its configured limits",
                    "Kubernetes terminated the workload",
                ],
            ))
        elif status == "Unknown":
            issues.append(self._issue(
                severity="warning",
                category="pod_status",
                title="Pod status is Unknown",
                evidence=["Kubernetes reports the pod phase as Unknown."],
                possible_causes=[
                    "Node communication issue",
                    "Kubelet is unavailable",
                    "Cluster networking problem",
                ],
            ))

        if status == "Running":
            for condition in pod.get("conditions") or []:
                if condition.get("type") == "Ready" and condition.get("status") == "False":
                    issues.append(self._issue(severity="warning", category="readiness",
                        title="Pod is not ready", evidence=[condition.get("message") or "Ready=False"],
                        possible_causes=["Review container readiness and application startup."], pod=pod.get("name")))

        reason = str(pod.get("reason") or "")
        message = str(pod.get("message") or "")
        if reason == "Evicted":
            issues.append(self._issue(
                severity="critical",
                category="pod_status",
                title="Pod was evicted from its node",
                evidence=[message or "Kubernetes evicted this pod."],
                possible_causes=[
                    "Node memory pressure",
                    "Node disk pressure",
                    "Ephemeral storage exhaustion",
                    "Resource limits or requests are too high",
                ],
            ))

    # =========================================================
    # POD SUMMARY
    # =========================================================

    def _detect_unhealthy_pod_summaries(
        self, pod: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(pod, list):
            return
        for item in pod:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "unknown")
            status = str(item.get("status") or "")
            try:
                restarts = int(item.get("restarts") or 0)
            except (TypeError, ValueError):
                restarts = 0
            ready = str(item.get("ready") or "")

            if status in {"Failed", "Unknown"}:
                issues.append(self._issue(
                    severity="critical" if status == "Failed" else "warning",
                    category="pod_status",
                    title=f"Pod '{name}' is in {status} state",
                    evidence=[f"Pod status: {status}"],
                    possible_causes=[
                        "Container failure",
                        "Application startup failure",
                        "Node or scheduling issue",
                    ],
                    pod=name,
                ))
            if ready.startswith("0/") or ready == "0":
                issues.append(self._issue(
                    severity="warning",
                    category="readiness",
                    title=f"Pod '{name}' has no ready containers",
                    evidence=[f"Ready status: {ready}"],
                    possible_causes=[
                        "Container is crashing",
                        "Readiness probe failure",
                        "Container startup failure",
                    ],
                    pod=name,
                ))
            if restarts >= 10:
                issues.append(self._issue(
                    severity="critical",
                    category="restarts",
                    title=f"Pod '{name}' has restarted {restarts} times",
                    evidence=[f"Restart count: {restarts}"],
                    possible_causes=[
                        "Application crashes",
                        "Liveness probe failures",
                        "Memory exhaustion",
                        "Dependency failures",
                    ],
                    pod=name,
                ))

    # =========================================================
    # CONTAINERS
    # =========================================================

    def _detect_container_issues(
        self, pod: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(pod, dict):
            return
        containers = pod.get("containers") or []
        if not isinstance(containers, list):
            return
        for container in containers:
            if not isinstance(container, dict):
                continue
            self._analyze_container(
                container=container, issues=issues, container_type="container",
            )

    def _detect_init_container_issues(
        self, pod: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(pod, dict):
            return
        init_containers = pod.get("init_containers") or []
        if not isinstance(init_containers, list):
            return
        for container in init_containers:
            if not isinstance(container, dict):
                continue
            self._analyze_container(
                container=container, issues=issues,
                container_type="init container",
            )

    def _analyze_container(
        self,
        container: dict[str, Any],
        issues: list[dict[str, Any]],
        container_type: str,
    ) -> None:
        name = str(container.get("name") or "unknown")
        state = container.get("state") or {}
        if not isinstance(state, dict):
            state = {}
        waiting = state.get("waiting") or {}
        terminated = state.get("terminated") or {}
        if not isinstance(waiting, dict):
            waiting = {}
        if not isinstance(terminated, dict):
            terminated = {}

        waiting_reason = str(waiting.get("reason") or "")
        terminated_reason = str(terminated.get("reason") or "")

        waiting_rules = {
            "CrashLoopBackOff": (
                "critical", "container",
                f"{container_type.title()} '{name}' is in CrashLoopBackOff",
                [
                    "Application crashes during startup",
                    "Invalid environment configuration",
                    "Missing dependency or secret",
                    "Incorrect command or arguments",
                    "Application configuration error",
                ],
            ),
            "ImagePullBackOff": (
                "critical", "image",
                f"{container_type.title()} '{name}' cannot pull its image",
                [
                    "Image does not exist", "Incorrect image tag",
                    "Registry authentication failure",
                    "Image pull secret is missing", "Registry is unavailable",
                ],
            ),
            "ErrImagePull": (
                "critical", "image",
                f"{container_type.title()} '{name}' failed to pull image",
                [
                    "Invalid image name", "Invalid image tag",
                    "Private registry authentication failure",
                    "Network problem reaching registry",
                ],
            ),
            "InvalidImageName": (
                "critical", "image",
                f"{container_type.title()} '{name}' has an invalid image name",
                [
                    "Malformed container image name", "Invalid registry path",
                    "Invalid image tag",
                ],
            ),
            "CreateContainerConfigError": (
                "critical", "configuration",
                f"{container_type.title()} '{name}' has a configuration error",
                [
                    "Missing ConfigMap", "Missing Secret",
                    "Invalid environment variable configuration",
                    "Invalid volume configuration",
                ],
            ),
            "CreateContainerError": (
                "critical", "container",
                f"{container_type.title()} '{name}' could not be created",
                [
                    "Container runtime failure", "Invalid mount configuration",
                    "Security context problem", "Invalid container configuration",
                ],
            ),
            "RunContainerError": (
                "critical", "container",
                f"{container_type.title()} '{name}' failed to start",
                [
                    "Invalid startup command", "Container runtime failure",
                    "Permission problem", "Invalid security configuration",
                ],
            ),
            "CreatePodSandbox": (
                "critical", "network", "Pod sandbox could not be created",
                [
                    "Container network interface failure", "CNI plugin problem",
                    "Node networking problem", "Container runtime issue",
                ],
            ),
            "FailedCreatePodSandBox": (
                "critical", "network", "Kubernetes failed to create pod sandbox",
                [
                    "CNI plugin failure", "Node networking problem",
                    "Container runtime failure", "IP address allocation problem",
                ],
            ),
        }
        rule = waiting_rules.get(waiting_reason)
        if rule:
            severity, category, title, causes = rule
            issues.append(self._issue(
                severity=severity, category=category, title=title,
                evidence=[str(
                    waiting.get("message") or f"Waiting reason: {waiting_reason}"
                )],
                possible_causes=causes, container=name,
            ))
        elif waiting_reason:
            issues.append(self._issue(
                severity="warning", category="container",
                title=f"{container_type.title()} '{name}' is waiting",
                evidence=[
                    f"Waiting reason: {waiting_reason}",
                    str(waiting.get("message") or ""),
                ],
                possible_causes=[
                    "Container initialization problem", "Dependency unavailable",
                    "Kubernetes startup issue",
                ],
                container=name,
            ))

        terminated_rules = {
            "OOMKilled": (
                "critical", "resources",
                f"{container_type.title()} '{name}' was OOMKilled",
                [
                    "Memory limit is too low", "Application memory leak",
                    "Unexpected memory spike", "Insufficient node memory",
                ],
            ),
            "Error": (
                "critical", "container",
                f"{container_type.title()} '{name}' terminated with an error",
                [
                    "Application crashed", "Startup command failed",
                    "Configuration error", "Dependency connection failure",
                ],
            ),
            "ContainerCannotRun": (
                "critical", "container",
                f"{container_type.title()} '{name}' cannot run",
                [
                    "Invalid container command", "Missing executable",
                    "Permission problem", "Invalid container image",
                ],
            ),
        }

        rule = terminated_rules.get(terminated_reason)
        if rule:
            severity, category, title, causes = rule
            evidence_value = (
                terminated.get("message")
                or f"Container termination reason: {terminated_reason}"
            )
            # Keep the explicit reason and source for OOMKilled even when
            # Kubernetes also supplies a termination message.
            if terminated_reason == "OOMKilled":
                evidence = self._oom_termination_evidence(
                    terminated, "state.terminated", name,
                )
                last_state = container.get("last_state")
                if isinstance(last_state, dict):
                    previous = last_state.get("terminated")
                    if (
                        isinstance(previous, dict)
                        and previous.get("reason") == "OOMKilled"
                    ):
                        evidence.extend(self._oom_termination_evidence(
                            previous, "last_state.terminated", name,
                        ))
            else:
                evidence = [str(evidence_value)]
            issues.append(self._issue(
                severity=severity, category=category, title=title,
                evidence=evidence, possible_causes=causes, container=name,
            ))

        # A restarted container may now be waiting or running while its
        # previous termination carries the OOMKilled evidence.
        last_state = container.get("last_state")
        if not isinstance(last_state, dict):
            return
        previous = last_state.get("terminated")
        if not isinstance(previous, dict):
            return
        if (
            previous.get("reason") == "OOMKilled"
            and terminated_reason != "OOMKilled"
        ):
            severity, category, title, causes = terminated_rules["OOMKilled"]
            issues.append(self._issue(
                severity=severity, category=category, title=title,
                evidence=self._oom_termination_evidence(
                    previous, "last_state.terminated", name,
                ),
                possible_causes=causes, container=name,
            ))

    @staticmethod
    def _oom_termination_evidence(
        terminated: dict[str, Any], source: str, name: str,
    ) -> list[str]:
        evidence = [f"Container '{name}': {source}.reason=OOMKilled"]
        # Preserve returned fields without inferring the memory limit,
        # a leak, or an ongoing failure from the termination alone.
        for field in (
            "message", "exitCode", "exit_code", "signal",
            "startedAt", "started_at", "finishedAt", "finished_at",
        ):
            value = terminated.get(field)
            if value is not None and str(value).strip():
                evidence.append(f"Container '{name}': {source}.{field}={value}")
        return evidence

    # =========================================================
    # RESTARTS
    # =========================================================

    def _detect_restart_issues(
        self, pod: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(pod, dict):
            return
        containers = pod.get("containers") or []
        if not isinstance(containers, list):
            return
        for container in containers:
            if not isinstance(container, dict):
                continue
            try:
                restart_count = int(container.get("restart_count") or 0)
            except (TypeError, ValueError):
                restart_count = 0
            if restart_count >= 10:
                severity = "critical"
            elif restart_count >= 3:
                severity = "warning"
            else:
                continue
            name = str(container.get("name") or "unknown")
            issues.append(self._issue(
                severity=severity, category="restarts",
                title=f"Container '{name}' has restarted {restart_count} times",
                evidence=[f"Restart count: {restart_count}"],
                possible_causes=[
                    "Application crashes", "Liveness probe failures",
                    "Memory exhaustion", "Dependency failures",
                ],
                container=name,
            ))

    # =========================================================
    # EVENTS
    # =========================================================

    def _detect_events(
        self, events_data: Any, issues: list[dict[str, Any]],
    ) -> None:
        if isinstance(events_data, list):
            events_data = {"events": events_data}
        if not isinstance(events_data, dict):
            return
        events = events_data.get("events") or []
        if not isinstance(events, list):
            return
        event_rules = {
            "FailedScheduling": (
                "critical", "Pod cannot be scheduled",
                [
                    "Insufficient CPU or memory", "Node selector mismatch",
                    "Taints are preventing scheduling",
                    "Affinity requirements cannot be satisfied",
                ],
            ),
            "FailedMount": (
                "critical", "Pod failed to mount a volume",
                [
                    "Persistent volume unavailable",
                    "Persistent volume claim is not bound",
                    "Secret or ConfigMap is missing", "Storage provider problem",
                ],
            ),
            "FailedAttachVolume": (
                "critical", "Pod failed to attach a volume",
                [
                    "Persistent volume attachment failure",
                    "Storage provider problem", "Volume already attached elsewhere",
                    "Node availability problem",
                ],
            ),
            "FailedCreatePodSandBox": (
                "critical", "Pod network sandbox creation failed",
                [
                    "CNI plugin failure", "Node networking issue",
                    "Container runtime failure", "IP allocation failure",
                ],
            ),
            "NetworkNotReady": (
                "critical", "Node network is not ready",
                [
                    "CNI plugin is not functioning",
                    "Node network configuration problem",
                    "Container networking service failure",
                ],
            ),
            "BackOff": (
                "warning", "Container is repeatedly backing off",
                [
                    "Container crashes repeatedly", "Application startup failure",
                    "Dependency is unavailable",
                ],
            ),
            "Unhealthy": (
                "warning", "Container health check is failing",
                [
                    "Readiness probe failure", "Liveness probe failure",
                    "Application is not listening on expected port",
                    "Application startup is too slow",
                ],
            ),
            "Failed": (
                "critical", "Kubernetes reported a failure event",
                [
                    "Container or pod startup failed",
                    "Resource configuration issue",
                    "Dependency or infrastructure failure",
                ],
            ),
        }
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type") or "")
            reason = str(event.get("reason") or "")
            message = str(event.get("message") or "")
            rule = event_rules.get(reason)
            if rule:
                severity, title, causes = rule
                issues.append(self._issue(
                    severity=severity, category={"FailedScheduling": "scheduling", "FailedMount": "storage", "FailedAttachVolume": "storage", "FailedCreatePodSandBox": "network", "NetworkNotReady": "network", "Unhealthy": "probe"}.get(reason, "event"), title=title,
                    evidence=[f"{reason}: {message or reason}"], possible_causes=causes,
                    pod=(event.get("involved_object") or {}).get("name") if (event.get("involved_object") or {}).get("kind") == "Pod" else None,
                ))
            elif event_type == "Warning":
                issues.append(self._issue(
                    severity="warning", category="event",
                    title=f"Kubernetes warning: {reason or 'Unknown'}",
                    evidence=[message or reason or "Kubernetes warning detected."],
                    possible_causes=[
                        "Review Kubernetes event details",
                        "Check related pod and container status",
                    ],
                ))

    # =========================================================
    # LOGS
    # =========================================================

    def _detect_log_patterns(
        self, logs_data: Any, issues: list[dict[str, Any]],
    ) -> None:
        current_logs = self._extract_current_logs(logs_data)
        self._analyze_log_collection(
            logs=current_logs, issues=issues, log_source="current",
        )

    def _detect_previous_log_patterns(
        self, logs_data: Any, issues: list[dict[str, Any]],
    ) -> None:
        previous_logs = self._extract_previous_logs(logs_data)
        if not previous_logs:
            return
        self._analyze_log_collection(
            logs=previous_logs, issues=issues, log_source="previous",
        )

    def _extract_current_logs(self, logs_data: Any) -> dict[str, Any]:
        if not isinstance(logs_data, dict):
            return {}
        # New collector format: containers -> container name -> logs.
        containers = logs_data.get("containers")
        if isinstance(containers, dict):
            normalized: dict[str, Any] = {}
            for container_name, container_data in containers.items():
                name = str(container_name or "").strip()
                if not name:
                    continue
                normalized[name] = self._extract_log_payload(container_data)
            return normalized
        # Older format: current -> container name -> log payload.
        current = logs_data.get("current")
        if isinstance(current, dict):
            return current
        # Direct legacy pod log structure.
        if "logs" in logs_data:
            container_name = str(
                logs_data.get("container") or logs_data.get("pod") or "container"
            )
            return {container_name: logs_data}
        return {}

    def _extract_previous_logs(self, logs_data: Any) -> dict[str, Any]:
        if not isinstance(logs_data, dict):
            return {}
        previous = logs_data.get("previous")
        if not isinstance(previous, dict):
            return {}
        return previous

    @staticmethod
    def _extract_log_payload(container_data: Any) -> Any:
        if not isinstance(container_data, dict):
            return container_data
        if "logs" in container_data:
            return container_data.get("logs")
        return container_data

    def _analyze_log_collection(
        self, logs: Any, issues: list[dict[str, Any]], log_source: str,
    ) -> None:
        if not isinstance(logs, dict):
            return
        for container_name, log_data in logs.items():
            text = self._normalize_log_text(log_data)
            if not text.strip():
                continue
            lowered = text.lower()
            connection_refused_matches = self._find_matching_log_lines(
                text=text, pattern="connection refused",
            )
            if connection_refused_matches:
                if self._contains_loopback_endpoint("\n".join(connection_refused_matches)):
                    issues.append(self._issue(
                        severity="warning", category="local_endpoint",
                        title="Local application endpoint is unavailable",
                        evidence=connection_refused_matches,
                        possible_causes=[
                            "The target process is not running",
                            "The target application failed during startup",
                            "The target port is not listening",
                            "The target application is repeatedly restarting",
                        ],
                        container=container_name,
                    ))
                else:
                    issues.append(self._issue(
                        severity="warning", category="network",
                        title="Dependency connection refused",
                        evidence=connection_refused_matches,
                        possible_causes=[
                            "Target service is unavailable",
                            "Incorrect host or port",
                            "Network policy blocking traffic",
                        ],
                        container=container_name,
                    ))

            patterns = [
                ("no such host", "DNS resolution failure detected", "warning", "network", ["Review the hostname and DNS service."]),
                ("nxdomain", "DNS resolution failure detected", "warning", "network", ["Review the queried DNS name."]),
                ("eai_again", "DNS resolution failure detected", "warning", "network", ["Review DNS availability."]),
                ("getaddrinfo enotfound", "DNS resolution failure detected", "warning", "network", ["Review the hostname and DNS configuration."]),
                ("network is unreachable", "Network route is unavailable", "warning", "network", ["Review routes and network connectivity."]),
                ("no route to host", "Network route is unavailable", "warning", "network", ["Review routes and network connectivity."]),

                (
                    "authentication failed", "Authentication failure detected",
                    "warning", "authentication",
                    [
                        "Invalid credentials", "Expired secret",
                        "Incorrect authentication configuration",
                    ],
                ),
                (
                    "permission denied", "Permission denied detected",
                    "warning", "authorization",
                    [
                        "Insufficient filesystem permissions",
                        "Invalid security context", "Missing RBAC permissions",
                    ],
                ),
                (
                    "out of memory", "Out of memory error detected",
                    "critical", "resources",
                    [
                        "Memory limit is too low",
                        "Application memory usage increased unexpectedly",
                        "Memory leak",
                    ],
                ),
                (
                    "fatal", "Fatal application error detected",
                    "critical", "logs",
                    [
                        "Application startup failure", "Unhandled application error",
                        "Invalid configuration",
                    ],
                ),
                (
                    "exception", "Application exception detected",
                    "warning", "logs",
                    [
                        "Unhandled application exception", "Invalid configuration",
                        "Dependency failure",
                    ],
                ),
                (
                    "timeout", "Application timeout detected",
                    "warning", "network",
                    [
                        "Dependency is responding slowly", "Network latency",
                        "Incorrect timeout configuration",
                    ],
                ),
                (
                    "timed out", "Connection timeout detected",
                    "warning", "network",
                    [
                        "Dependency is unavailable", "Network connectivity issue",
                        "Service response is too slow",
                    ],
                ),
                (
                    "name or service not known", "DNS resolution failure detected",
                    "warning", "network",
                    ["Invalid hostname", "DNS service problem", "Kubernetes DNS issue"],
                ),
                (
                    "temporary failure in name resolution",
                    "DNS resolution failure detected", "warning", "network",
                    ["CoreDNS problem", "Invalid hostname", "Cluster networking issue"],
                ),
                (
                    "certificate verify failed", "TLS certificate validation failed",
                    "warning", "tls",
                    [
                        "Expired certificate", "Invalid certificate chain",
                        "Incorrect CA configuration",
                    ],
                ),
                (
                    "connection reset", "Connection reset detected",
                    "warning", "network",
                    [
                        "Remote service closed the connection", "Network interruption",
                        "Load balancer or proxy problem",
                    ],
                ),
            ]
            for pattern, title, severity, category, causes in patterns:
                if pattern not in lowered and not (
                    pattern == "timeout" and any(is_timeout_failure(line) for line in text.splitlines())
                ):
                    continue
                evidence = self._find_matching_log_lines(text=text, pattern=pattern)
                if pattern in {"timeout", "timed out"}:
                    evidence = list(dict.fromkeys(
                        line.strip() for line in text.splitlines()
                        if is_timeout_failure(line)
                    ))[:5]
                    if not evidence:
                        continue
                issues.append(self._issue(
                    severity=severity, category=category, title=title,
                    evidence=evidence or [
                        f"Pattern '{pattern}' found in {log_source} logs for "
                        f"'{container_name}'."
                    ],
                    possible_causes=causes, container=container_name,
                ))

            self._detect_configuration_log_errors(
                text=text, issues=issues, container_name=container_name,
                log_source=log_source,
            )
            ts_matches = self._find_regex_lines(
                text=text,
                patterns=[r"error\s+TS\d{3,5}:", r"TS\d{3,5}:", r"error TS\d+"],
                limit=5,
            )
            if ts_matches:
                issues.append(self._issue(
                    severity="critical", category="build",
                    title="TypeScript compilation error detected in application logs",
                    evidence=ts_matches,
                    possible_causes=[
                        "TypeScript compilation failure", "Missing type declaration",
                        "Missing dependency types", "Invalid TypeScript code",
                        "Dependency version mismatch",
                    ],
                    container=container_name,
                ))
            build_matches = self._find_regex_lines(
                text=text,
                patterns=[
                    r"\bcompilation failed\b", r"\bbuild failed\b",
                    r"\bfailed to compile\b", r"\btsc\b.*\berror\b",
                ],
                limit=5,
            )
            if build_matches:
                issues.append(self._issue(
                    severity="critical", category="build",
                    title="Application build failure detected",
                    evidence=build_matches,
                    possible_causes=[
                        "Source code compilation failure", "Missing dependency",
                        "Dependency version mismatch", "Build configuration error",
                    ],
                    container=container_name,
                ))

    # =========================================================
    # CONFIGURATION LOG ERRORS
    # =========================================================

    def _detect_configuration_log_errors(
        self,
        text: str,
        issues: list[dict[str, Any]],
        container_name: str,
        log_source: str,
    ) -> None:
        yaml_patterns = [
            r"did not find expected key", r"did not find expected ':'",
            r"yaml:\s+line\s+\d+", r"yaml.*parse", r"yaml.*parsing",
            r"yaml.*syntax", r"error loading config", r"failed to load config",
            r"cannot load config", r"invalid.*config", r"configuration.*error",
            r"parsing yaml", r"yaml.*scanner error", r"while parsing",
            r"could not find expected key",
        ]
        compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in yaml_patterns
        ]
        matched_evidence: list[str] = []
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if any(pattern.search(cleaned) for pattern in compiled_patterns):
                if cleaned not in matched_evidence:
                    matched_evidence.append(cleaned)
            if len(matched_evidence) >= 5:
                break
        if not matched_evidence:
            return
        issues.append(self._issue(
            severity="critical", category="configuration",
            title="Configuration parsing error detected",
            evidence=matched_evidence,
            possible_causes=[
                "Invalid YAML syntax", "Malformed configuration file",
                "Incorrect configuration structure",
            ],
            container=container_name,
        ))

    # =========================================================
    # HTTP
    # =========================================================

    def _detect_http_errors(
        self, logs_data: Any, issues: list[dict[str, Any]],
    ) -> None:
        current_logs = self._extract_current_logs(logs_data)
        if not isinstance(current_logs, dict):
            return
        http_rules = {
            "401": (
                "info", "HTTP 401 responses observed",
                [
                    "Invalid user credentials", "Expired authentication token",
                    "Authentication configuration issue",
                ],
            ),
            "403": (
                "warning", "HTTP authorization failures detected",
                [
                    "User or service lacks required permissions",
                    "Incorrect RBAC configuration",
                    "Application authorization policy is blocking access",
                ],
            ),
            "404": (
                "info", "HTTP resource not found responses detected",
                [
                    "Incorrect application route", "Missing API endpoint",
                    "Incorrect URL configuration",
                ],
            ),
            "500": (
                "critical", "HTTP internal server errors detected",
                [
                    "Unhandled application exception", "Dependency failure",
                    "Application configuration error",
                ],
            ),
            "502": (
                "critical", "HTTP bad gateway responses detected",
                [
                    "Upstream application is unavailable",
                    "Reverse proxy configuration issue", "Network connectivity problem",
                ],
            ),
            "503": (
                "critical", "HTTP service unavailable responses detected",
                [
                    "Application service is unavailable", "No healthy backend endpoints",
                    "Service overload",
                ],
            ),
            "504": (
                "critical", "HTTP gateway timeout responses detected",
                [
                    "Upstream service is responding too slowly", "Dependency timeout",
                    "Network latency",
                ],
            ),
        }
        for container_name, log_data in current_logs.items():
            text = self._normalize_log_text(log_data)
            for status_code, rule in http_rules.items():
                pattern = rf'"\s+{status_code}\s'
                matches = re.findall(pattern, text)
                if not matches:
                    continue
                severity, title, causes = rule
                evidence = self._find_http_log_lines(text=text, status_code=status_code)
                issues.append(self._issue(
                    severity=severity, category="http", title=title,
                    evidence=evidence or [
                        f"Detected {len(matches)} HTTP {status_code} response(s) in "
                        f"'{container_name}'."
                    ],
                    possible_causes=causes, container=container_name,
                ))

    # =========================================================
    # NODES
    # =========================================================

    def _detect_node_conditions(
        self, nodes: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(nodes, list):
            return
        condition_rules = {
            "MemoryPressure": (
                "critical", "Node is under memory pressure",
                [
                    "Insufficient available node memory", "High pod memory consumption",
                    "Memory requests are too large",
                ],
            ),
            "DiskPressure": (
                "critical", "Node is under disk pressure",
                [
                    "Insufficient node disk space", "Container image or log growth",
                    "Ephemeral storage exhaustion",
                ],
            ),
            "PIDPressure": (
                "critical", "Node is under PID pressure",
                [
                    "Too many processes on the node", "Container process leak",
                    "Node process limit reached",
                ],
            ),
            "Ready": (
                "critical", "Node is not Ready",
                [
                    "Kubelet failure", "Node networking issue",
                    "Infrastructure or instance failure",
                ],
            ),
        }
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_name = str(node.get("name") or "unknown")
            conditions = node.get("conditions") or []
            if not isinstance(conditions, list):
                continue
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue
                condition_type = str(condition.get("type") or "")
                condition_status = str(condition.get("status") or "")
                if condition_type == "Ready":
                    if condition_status not in {"False", "Unknown"}:
                        continue
                    rule = condition_rules["Ready"]
                elif condition_type in {"MemoryPressure", "DiskPressure", "PIDPressure"}:
                    if condition_status != "True":
                        continue
                    rule = condition_rules[condition_type]
                else:
                    continue
                severity, title, causes = rule
                evidence = condition.get("message") or (
                    f"Node '{node_name}' has {condition_type}={condition_status}."
                )
                issues.append(self._issue(
                    severity=severity, category="node", title=title,
                    evidence=[str(evidence)], possible_causes=causes, node=node_name,
                ))

    # =========================================================
    # NODE METRICS
    # =========================================================

    def _detect_node_metrics(
        self, metrics: Any, issues: list[dict[str, Any]],
    ) -> None:
        if not isinstance(metrics, dict):
            return
        nodes = metrics.get("nodes") or []
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = str(node.get("name") or "unknown")
            memory_percent = self._parse_percent(node.get("memory_percent"))
            cpu_percent = self._parse_percent(node.get("cpu_percent"))
            if memory_percent is not None and memory_percent >= 90:
                issues.append(self._issue(
                    severity="critical", category="resources",
                    title=f"Node '{name}' has high memory utilization",
                    evidence=[f"Node memory utilization: {memory_percent}%"],
                    possible_causes=[
                        "High pod memory consumption", "Node memory capacity is insufficient",
                        "Memory requests are too high",
                    ],
                    node=name,
                ))
            if cpu_percent is not None and cpu_percent >= 90:
                issues.append(self._issue(
                    severity="warning", category="resources",
                    title=f"Node '{name}' has high CPU utilization",
                    evidence=[f"Node CPU utilization: {cpu_percent}%"],
                    possible_causes=[
                        "High pod CPU consumption", "Node CPU capacity is insufficient",
                        "CPU requests are too high",
                    ],
                    node=name,
                ))

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _contains_loopback_endpoint(text: str) -> bool:
        lowered = text.lower()
        return (
            "127.0.0.1" in lowered or "localhost" in lowered
            or "[::1]" in lowered or "::1:" in lowered
        )

    @staticmethod
    def _find_matching_log_lines(
        text: str, pattern: str, limit: int = 5,
    ) -> list[str]:
        matches: list[str] = []
        for line in text.splitlines():
            if pattern.lower() in line.lower():
                cleaned = line.strip()
                if cleaned:
                    matches.append(cleaned)
            if len(matches) >= limit:
                break
        return matches

    @staticmethod
    def _find_regex_lines(
        text: str, patterns: list[str], limit: int = 5,
    ) -> list[str]:
        compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        matches: list[str] = []
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if any(pattern.search(cleaned) for pattern in compiled):
                matches.append(cleaned)
            if len(matches) >= limit:
                break
        return matches

    @staticmethod
    def _find_http_log_lines(
        text: str, status_code: str, limit: int = 5,
    ) -> list[str]:
        matches: list[str] = []
        pattern = re.compile(rf'"\s+{status_code}\s')
        for line in text.splitlines():
            if pattern.search(line):
                cleaned = line.strip()
                if cleaned:
                    matches.append(cleaned)
            if len(matches) >= limit:
                break
        return matches

    @staticmethod
    def _normalize_log_text(log_data: Any) -> str:
        if isinstance(log_data, list):
            return "\n".join(str(line) for line in log_data)
        if log_data is None:
            return ""
        if isinstance(log_data, dict):
            nested_logs = log_data.get("logs")
            if isinstance(nested_logs, list):
                return "\n".join(str(line) for line in nested_logs)
        return str(log_data)

    @staticmethod
    def _parse_percent(value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().replace("%", "")
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _issue(
        severity: str,
        category: str,
        title: str,
        evidence: list[str] | str,
        possible_causes: list[str],
        container: str | None = None,
        pod: str | None = None,
        node: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(evidence, str):
            normalized_evidence = [evidence]
        else:
            normalized_evidence = [str(item) for item in evidence if str(item).strip()]
        issue: dict[str, Any] = {
            "severity": severity, "category": category, "title": title,
            "evidence": normalized_evidence, "possible_causes": possible_causes,
        }
        if container:
            issue["container"] = container
        if pod:
            issue["pod"] = pod
        if node:
            issue["node"] = node
        return issue

    @staticmethod
    def _deduplicate(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str | None, str | None, str | None]] = set()
        for issue in issues:
            key = (
                str(issue.get("category") or ""), str(issue.get("title") or ""),
                issue.get("container"), issue.get("pod"), issue.get("node"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(issue)
        return unique
