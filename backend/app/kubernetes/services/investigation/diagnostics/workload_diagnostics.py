"""Evidence-only checks for workloads, service routing and resource pressure."""
from __future__ import annotations
from typing import Any


def section(evidence, name):
    value = evidence.get(name)
    if isinstance(value, dict) and value.get('status') in {'collected', 'failed', 'skipped'}:
        return value.get('data') if value['status'] == 'collected' else None
    return value


def items(value):
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return [value] if isinstance(value, dict) else []


class WorkloadDiagnosticsService:
    def analyze(self, evidence: dict[str, Any]) -> list[dict[str, Any]]:
        findings = []

        def add(category, title, severity, confidence, proof, actions, **scope):
            findings.append(dict(category=category, title=title, severity=severity,
                confidence=confidence, evidence=proof, possible_causes=[],
                recommended_actions=actions, verified_finding=True, **scope))

        pods = items(section(evidence, 'pod'))
        events = section(evidence, 'events')
        events = events.get('events', []) if isinstance(events, dict) else (events or [])
        for pod in pods:
            for condition in pod.get('conditions', []):
                if condition.get('type') == 'PodScheduled' and condition.get('status') == 'False':
                    # SchedulingGated is intentional, not a scheduler failure.
                    if condition.get('reason') != 'Unschedulable':
                        continue
                    if any(e.get('reason') == 'FailedScheduling' and e.get('involved_object', {}).get('name') == pod.get('name') for e in events):
                        continue
                    add('scheduling', 'Pod cannot be scheduled', 'critical', 90,
                        [f"Pod {pod.get('name')}: PodScheduled=False, reason=Unschedulable", condition.get('message', '')],
                        ['Review the scheduler message.', 'Check requests, taints, selectors and volume binding.'], pod=pod.get('name'))

        for deployment in items(section(evidence, 'deployment')):
            name = deployment.get('name', 'unknown')
            if deployment.get('paused') or deployment.get('replicas') == 0:
                continue
            if deployment.get('observed_generation', 0) < deployment.get('generation', 0):
                add('deployment', f"Deployment '{name}' update is awaiting observation", 'info', 80,
                    [f"generation={deployment.get('generation')}, observedGeneration={deployment.get('observed_generation')}"],
                    ['Recheck deployment status after the controller observes this generation.'], deployment=name)
                continue
            failed = False
            for c in deployment.get('conditions', []):
                reason = c.get('reason', '')
                if (c.get('type') == 'Progressing' and c.get('status') == 'False' and reason == 'ProgressDeadlineExceeded') or (c.get('type') == 'ReplicaFailure' and c.get('status') == 'True'):
                    failed = True
                    add('deployment', f"Deployment '{name}' rollout failed", 'critical', 95,
                        [f"{c.get('type')}={c.get('status')}: {reason}", c.get('message', '')],
                        ['Review related ReplicaSet and pod events.', 'Resolve the pod failure before retrying the rollout.'], deployment=name)
            if not failed and deployment.get('available_replicas', 0) < deployment.get('replicas', 0):
                add('deployment', f"Deployment '{name}' has unavailable replicas", 'warning', 80,
                    [f"desired={deployment.get('replicas')}, available={deployment.get('available_replicas', 0)}, updated={deployment.get('updated_replicas', 0)}"],
                    ['Check related pod readiness and events.', 'Recheck rollout progress; replica shortage alone does not prove a stalled rollout.'], deployment=name)

        pod_inventory = section(evidence, 'pod')
        slices = section(evidence, 'endpoints')
        for service in items(section(evidence, 'services')):
            if service.get('type') == 'ExternalName':
                continue
            name = service.get('name', 'unknown')
            selector = service.get('selector') or {}
            # Only a full, successfully collected pod list proves no match.
            if selector and isinstance(pod_inventory, list):
                selected = [p for p in pods if all(p.get('labels', {}).get(k) == v for k, v in selector.items())]
                if not selected:
                    add('service', f"Service '{name}' selector matches no pods", 'critical', 95,
                        [f"Service {name} selector={selector}; matching pod count=0"],
                        ['Compare the Service selector with intended pod labels.', 'Check whether the intended workload exists or is scaled to zero.'], service=name)
                    continue
                # Only named target ports can be validated from declarations.
                for port in service.get('ports', []):
                    target = port.get('targetPort', port.get('port'))
                    if isinstance(target, str) and not target.isdigit():
                        missing = [p['name'] for p in selected if not any(cp.get('name') == target and cp.get('protocol', 'TCP') == port.get('protocol', 'TCP') for c in p.get('containers', []) + p.get('init_containers', []) for cp in c.get('ports', []))]
                        if missing:
                            add('service', f"Service '{name}' named targetPort is unresolved", 'critical', 95,
                                [f"targetPort={target}; missing on pods: {', '.join(missing)}"],
                                ['Match targetPort to a named container port with the same protocol.'], service=name)
            if not isinstance(slices, list):
                continue
            related = [s for s in slices if s.get('metadata', {}).get('labels', {}).get('kubernetes.io/service-name') == name]
            endpoints = [e for s in related for e in s.get('endpoints', [])]
            ready = [e for e in endpoints if e.get('addresses') and e.get('conditions', {}).get('ready') is not False and e.get('conditions', {}).get('terminating') is not True]
            if not ready:
                add('service', f"Service '{name}' has no ready non-terminating endpoints", 'critical', 90,
                    [f"EndpointSlices={len(related)}, endpoints={len(endpoints)}, ready non-terminating endpoints=0"],
                    ['Review EndpointSlice readiness and target pod health.', 'Check selectors or manually managed endpoints as applicable.'], service=name)

        for claim in items(section(evidence, 'pvc')):
            if claim.get('status') in {'Pending', 'Lost'}:
                add('storage', f"PVC '{claim.get('name')}' is {claim['status']}", 'critical' if claim['status'] == 'Lost' else 'warning', 85,
                    [f"PVC phase={claim['status']}; storageClass={claim.get('storage_class', '')}"],
                    ['Review PVC events and storage provisioning.', 'Check volume binding mode and capacity.'], pvc=claim.get('name'))

        # Quota values are quantities; compare identical units conservatively.
        from decimal import Decimal, InvalidOperation
        for quota in items(section(evidence, 'resource_quotas')):
            status = quota.get('status') or {}
            for resource, hard in status.get('hard', {}).items():
                used = status.get('used', {}).get(resource)
                if used is None:
                    continue
                try:
                    full = Decimal(str(used)) >= Decimal(str(hard))
                except InvalidOperation:
                    full = str(used) == str(hard)
                if full:
                    name = quota.get('metadata', {}).get('name')
                    add('resources', f"ResourceQuota '{name}' has reached {resource}", 'warning', 90,
                        [f"used={used}, hard={hard}; further allocation may be rejected"],
                        ['Review namespace quota usage and admission events.', 'Free resources or adjust quota if appropriate.'])
        return findings
