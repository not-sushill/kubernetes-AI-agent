from __future__ import annotations

import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.ai.service import AIService
from app.investigations.analysis import InvestigationAnalysisService
from app.investigations.collector import InvestigationCollector
from app.investigations.models import InvestigationCreate
from app.kubernetes.services.pod_service import PodService
from app.kubernetes.services.investigation.diagnostics.pod_diagnostics import PodDiagnosticsService
from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService


def analyze(**evidence):
    return InvestigationAnalysisService().analyze(evidence)


def container(state=None, last=None):
    return dict(name='app', state=state or {}, last_state=last or {})


@pytest.mark.parametrize('key', ['containers', 'init_containers'])
@pytest.mark.parametrize('current', ['terminated', 'waiting', 'running'])
def test_oom_paths(key, current):
    state = {current: {'reason': 'OOMKilled' if current == 'terminated' else 'CrashLoopBackOff'}}
    last = {'terminated': {'reason': 'OOMKilled', 'exitCode': 137, 'finishedAt': '2026-09-17T10:00:00Z'}} if current != 'terminated' else {}
    result = analyze(pod={key: [container(state, last)]})
    cause = result['root_causes'][0]
    assert cause['category'] == 'resources'
    assert cause['severity'] == 'critical'
    assert cause['confidence'] == 85
    assert any('OOMKilled' in e for e in cause['evidence'])
    assert len([i for i in result['diagnostics'] if 'OOMKilled' in i['title']]) == 1


@pytest.mark.parametrize('last', [None, [], 'bad', {}, {'terminated': []}, {'terminated': {'reason': 'Error', 'exitCode': 137}}])
def test_no_oom_from_missing_malformed_or_exit_code(last):
    result = analyze(pod={'containers': [container({'terminated': {'reason': 'Error', 'exitCode': 137}}, last)]})
    assert not any('OOMKilled' in i['title'] for i in result['diagnostics'])


def test_duplicate_oom_combines_sources():
    term = {'reason': 'OOMKilled', 'message': 'Killed', 'exitCode': 137}
    result = analyze(pod={'containers': [container({'terminated': term}, {'terminated': term})]})
    oom = [i for i in result['diagnostics'] if 'OOMKilled' in i['title']]
    assert len(oom) == 1
    assert any('last_state' in e for e in oom[0]['evidence'])
    assert any('state.terminated.reason=OOMKilled' in e for e in result['root_causes'][0]['evidence'])


def test_pending_is_not_scheduling_failure():
    assert not analyze(pod={'status': 'Pending'})['root_causes']


@pytest.mark.parametrize('shape', ['list', 'dict'])
def test_failed_scheduling_events(shape):
    events = [{'reason': 'FailedScheduling', 'type': 'Warning', 'message': '0/2 nodes: Insufficient memory'}]
    result = analyze(events=events if shape == 'list' else {'events': events})
    assert result['root_causes'][0]['category'] == 'scheduling'


def test_unschedulable_condition_and_gate():
    p = {'name': 'app', 'conditions': [{'type': 'PodScheduled', 'status': 'False', 'reason': 'Unschedulable', 'message': 'Insufficient cpu'}]}
    assert analyze(pod=p)['root_causes'][0]['category'] == 'scheduling'
    p['conditions'][0]['reason'] = 'SchedulingGated'
    assert not analyze(pod=p)['root_causes']


@pytest.mark.parametrize('kind', ['Readiness', 'Liveness', 'Startup'])
def test_distinct_probes(kind):
    result = analyze(events={'events': [{'reason': 'Unhealthy', 'message': f'{kind} probe failed: connection refused'}]})
    assert any(c['title'] == f'{kind} probe failure' for c in result['root_causes'])


@pytest.mark.parametrize('line', ['no such host', 'NXDOMAIN', 'EAI_AGAIN', 'getaddrinfo ENOTFOUND', 'temporary failure in name resolution'])
def test_dns_patterns(line):
    result = analyze(logs={'containers': {'app': {'logs': [line]}}})
    assert any(c['title'] == 'DNS or service discovery failure' for c in result['root_causes'])


def test_remote_refusal_not_misclassified_by_unrelated_localhost_line():
    result = analyze(logs={'containers': {'app': {'logs': ['server listening localhost:80', 'connect db:5432: connection refused']}}})
    assert result['root_causes'][0]['title'] == 'Remote dependency connection refused'


@pytest.mark.parametrize('reason', ['FailedCreatePodSandBox', 'NetworkNotReady'])
def test_network_events(reason):
    assert any(c['category'] == 'network' for c in analyze(events=[{'reason': reason, 'message': 'CNI failed'}])['root_causes'])


def test_rollout_deadline_and_scaled_zero():
    d = {'name': 'api', 'replicas': 2, 'available_replicas': 0, 'generation': 2, 'observed_generation': 2,
         'conditions': [{'type': 'Progressing', 'status': 'False', 'reason': 'ProgressDeadlineExceeded', 'message': 'Timed out progressing'}]}
    result = analyze(deployment=d)
    assert result['root_causes'][0]['title'] == "Deployment 'api' rollout failed"
    for field, value in [('replicas', 0), ('paused', True), ('observed_generation', 1)]:
        trial = dict(d, **{field: value})
        assert not any(c['severity'] == 'critical' for c in analyze(deployment=trial)['root_causes'])


def service_evidence():
    return {'pod': [{'name': 'api', 'labels': {'app': 'api'}, 'containers': [{'name': 'app', 'ports': [{'name': 'web', 'containerPort': 80}]}]}],
            'services': [{'name': 'api', 'type': 'ClusterIP', 'selector': {'app': 'api'}, 'ports': [{'port': 80, 'targetPort': 'web'}]}],
            'endpoints': [{'metadata': {'labels': {'kubernetes.io/service-name': 'api'}}, 'endpoints': [{'addresses': ['10.0.0.1'], 'conditions': {'ready': True}}]}]}


def test_healthy_service_and_numeric_target_not_declared():
    e = service_evidence()
    assert not analyze(**e)['root_causes']
    e['services'][0]['ports'][0]['targetPort'] = 9999
    assert not analyze(**e)['root_causes']


def test_selector_mismatch():
    e = service_evidence();e['pod'] = []
    assert 'selector matches no pods' in analyze(**e)['root_causes'][0]['title']


def test_named_target_port_missing():
    e = service_evidence();e['services'][0]['ports'][0]['targetPort'] = 'missing'
    assert 'targetPort is unresolved' in analyze(**e)['root_causes'][0]['title']


@pytest.mark.parametrize('value', [False, True, None])
def test_endpoint_readiness(value):
    e = service_evidence(); e['endpoints'][0]['endpoints'][0]['conditions']['ready'] = value
    causes = analyze(**e)['root_causes']
    assert bool(causes) is (value is False)


def test_failed_endpoint_collection_does_not_invent_absence():
    e = service_evidence();e['endpoints'] = {'status': 'failed', 'data': None, 'error': 'Forbidden'}
    assert not analyze(**e)['root_causes']


def test_external_name_and_selectorless_service():
    e = service_evidence(); e['pod'] = []
    e['services'][0]['type'] = 'ExternalName'
    assert not analyze(**e)['root_causes']
    e['services'][0]['type'] = 'ClusterIP';e['services'][0]['selector'] = {}
    assert not analyze(**e)['root_causes']


def test_multi_pod_different_failures_preserved():
    result = analyze(pod=[
        {'name': 'one', 'containers': [container({'waiting': {'reason': 'ImagePullBackOff', 'message': 'image tag not found'}})]},
        {'name': 'two', 'containers': [container({'waiting': {'reason': 'CrashLoopBackOff'}}, {'terminated': {'reason': 'OOMKilled'}})]},
    ], logs={'pods': {'three': {'containers': {'app': {'logs': ['TS7016: missing declaration']}}}}})
    causes = result['root_causes']
    assert {(c['pod'], c['category']) for c in causes} >= {('one', 'image'), ('two', 'resources'), ('three', 'build')}


def test_prometheus_configuration_remains_primary():
    result = analyze(logs={'containers': {
        'prometheus-server': {'logs': ['Error loading config /etc/config/prometheus.yml yaml: line 11: did not find expected key']},
        'reload': {'logs': ['localhost:9090 connection refused']},
    }})
    assert len(result['root_causes']) == 1
    assert result['root_causes'][0]['category'] == 'configuration'
    assert result['root_causes'][0]['confidence'] == 95


def test_node_pressure_and_quota():
    result = analyze(node=[{'name': 'worker', 'conditions': [{'type': 'MemoryPressure', 'status': 'True'}]}],
        resource_quotas=[{'metadata': {'name': 'limits'}, 'status': {'hard': {'pods': '5'}, 'used': {'pods': '5'}}}])
    assert len(result['root_causes']) == 2
    assert all(c['category'] == 'resources' for c in result['root_causes'])


@pytest.mark.parametrize('payload', [
    {'namespace': 'bad namespace'}, {'namespace': '-x'},
    {'namespace': 'default', 'resource_type': 'pod'},
    {'namespace': 'default', 'resource_type': 'deployment', 'resource_name': '../bad'},
    {'namespace': 'default', 'resource_type': 'service', 'resource_name': ''},
    {'namespace': 'default', 'log_tail': -1},
    {'namespace': 'default', 'log_tail': 5001},
])
def test_invalid_requests(payload):
    with pytest.raises(ValidationError):
        InvestigationCreate(**payload)


def test_pod_normalizer_keeps_init_and_resources():
    raw = {'metadata': {'name': 'api', 'labels': {'app': 'api'}},
           'spec': {'containers': [{'name': 'app', 'resources': {'limits': {'memory': '64Mi'}}, 'readinessProbe': {'tcpSocket': {'port': 80}}}], 'initContainers': [{'name': 'init'}]},
           'status': {'phase': 'Pending', 'initContainerStatuses': [{'name': 'init', 'state': {'waiting': {'reason': 'CrashLoopBackOff'}}, 'lastState': {'terminated': {'reason': 'OOMKilled'}}}], 'conditions': [{'type': 'PodScheduled', 'status': 'True'}]}}
    pod = PodService._normalize_pod(raw)
    assert pod['containers'][0]['resources']['limits']['memory'] == '64Mi'
    assert pod['containers'][0]['readiness_probe']['tcpSocket']['port'] == 80
    assert pod['init_containers'][0]['last_state']['terminated']['reason'] == 'OOMKilled'
    assert analyze(pod=pod)['root_causes'][0]['category'] == 'resources'


def test_label_expression_semantics():
    match = InvestigationCollector._matches_selector
    assert match({'app': 'api', 'zone': 'east'}, {'app': 'api'}, [{'key': 'zone', 'operator': 'In', 'values': ['east']}])
    assert not match({'app': 'api'}, {'app': 'api'}, [{'key': 'zone', 'operator': 'Exists'}])
    assert match({'app': 'api'}, {'app': 'api'}, [{'key': 'zone', 'operator': 'NotIn', 'values': ['east']}])
    assert not match({'app': 'api'}, {})


def test_collector_scopes_deployment_and_service():
    from tests.unit.test_investigations import FakeNamespaceService, FakePodService, FakeDeploymentService, FakeInventoryService
    inventory = FakeInventoryService()
    inventory.list_services = lambda ns: [{'name': 'api', 'selector': {'app': 'api'}}]
    pod_service = FakePodService()
    original = pod_service.list_pods
    pod_service.list_pods = lambda ns: original(ns) + [{'name': 'unrelated', 'labels': {'app': 'other'}, 'status': 'Failed'}]
    collector = InvestigationCollector(FakeNamespaceService(), pod_service, FakeDeploymentService(), inventory)
    for resource in ['deployment', 'service']:
        evidence = collector.collect(InvestigationCreate(namespace='default', resource_type=resource, resource_name='api'))
        assert {p['name'] for p in evidence.pod.data} == {'api-1', 'api-2'}
        assert set(evidence.logs.data['pods']) == {'api-1', 'api-2'}
        assert evidence.run_status() == 'COMPLETED'


CAUSE = dict(title='Container exceeded available memory', category='resources', severity='critical', confidence=85,
             description='Container termination reports OOMKilled.', evidence=['state.terminated.reason=OOMKilled'], recommended_actions=['Check memory usage.'])


@pytest.mark.parametrize('response', [None, 'not-json', '{"summary":"ok","severity":"INFO","confidence":0,"root_causes":[],"recommendations":[]}'])
def test_ai_failure_or_downgrade_preserves_finding(monkeypatch, response):
    monkeypatch.setattr(AIService, '_ai_enabled', staticmethod(lambda: True))
    client = Mock()
    if response is None:
        client.generate.side_effect = TimeoutError('Ollama timed out')
    else:
        client.generate.return_value = response
    result = AIService(client).diagnose(root_causes=[CAUSE])
    assert result.severity == 'CRITICAL'
    assert result.confidence == 85
    assert result.root_causes[0].title == CAUSE['title']
    assert result.recommendations
    if response in (None, 'not-json'):
        assert result.limitations


def test_ai_cannot_add_verified_causes_or_evidence(monkeypatch):
    monkeypatch.setattr(AIService, '_ai_enabled', staticmethod(lambda: True))
    client = Mock()
    client.generate.return_value = json.dumps({'summary': 'Model interpretation', 'severity': 'INFO', 'confidence': 0,
        'root_causes': [{'title': CAUSE['title'], 'explanation': 'a fake explanation', 'severity': 'INFO', 'confidence': 0, 'evidence': ['invented evidence']},
                        {'title': 'invented cause', 'explanation': 'invented', 'severity': 'CRITICAL', 'confidence': 100, 'evidence': ['invented']} ]})
    result = AIService(client).diagnose(root_causes=[CAUSE])
    assert len(result.root_causes) == 1
    assert result.root_causes[0].evidence == CAUSE['evidence']
    assert result.root_causes[0].explanation == CAUSE['description']


def test_warning_does_not_become_info():
    assert AIService._severity('warning') == 'MEDIUM'


@pytest.mark.parametrize('bad_summary', [None, {}, {'status': 'collected'}, [], '', '  ', "{'status': 'collected'}", 'No AI summary was generated.'])
def test_invalid_summary_is_retried_then_explicit_fallback(monkeypatch, bad_summary):
    monkeypatch.setattr(AIService, '_ai_enabled', staticmethod(lambda: True))
    client = Mock()
    client.generate.return_value = json.dumps({'summary': bad_summary})
    diagnosis = AIService(client).diagnose(root_causes=[CAUSE])
    assert client.generate.call_count == 2
    assert diagnosis.limitations
    assert diagnosis.severity == 'CRITICAL'
    assert diagnosis.confidence == 85
    assert 'AI analysis was unavailable' in diagnosis.summary


def test_summary_retry_can_recover(monkeypatch):
    monkeypatch.setattr(AIService, '_ai_enabled', staticmethod(lambda: True))
    client = Mock()
    client.generate.side_effect = [json.dumps({'summary': {'status': 'collected'}}), json.dumps({'summary': 'The recorded termination reason is OOMKilled.'})]
    diagnosis = AIService(client).diagnose(root_causes=[CAUSE])
    assert client.generate.call_count == 2
    assert not diagnosis.limitations
    assert 'recorded termination' in diagnosis.summary


@pytest.mark.parametrize('restarts,has_last,previous_calls', [(0, False, 0), (1, False, 1), (0, True, 1), (None, False, 1)])
def test_previous_logs_only_requested_when_applicable(restarts, has_last, previous_calls):
    pods = Mock()
    pods.get_logs.return_value = {'available': True, 'logs': []}
    collector = InvestigationCollector(pod_service=pods)
    metadata = {'name': 'app', 'restart_count': restarts, 'last_state': {'terminated': {'reason': 'OOMKilled'}} if has_last else {}}
    collector._collect_logs(InvestigationCreate(namespace='default', resource_type='pod', resource_name='api', include_previous_logs=True), {'containers': [metadata]})
    assert sum(call.kwargs['previous'] for call in pods.get_logs.call_args_list) == previous_calls


def test_cpu_prompt_is_bounded_and_excludes_raw_cluster_data():
    prompt = AIService._build_prompt(
        diagnostics=[], root_causes=[dict(CAUSE, title=str(i), evidence=['x' * 2000]) for i in range(200)],
        evidence={'secret_raw_marker': 'do not send raw cluster inventory'})
    assert len(prompt) < 6000
    assert 'secret_raw_marker' not in prompt
    assert json.loads(prompt)['omitted_findings'] > 0


def test_ai_serialization_has_real_enum_and_ignores_generated_actions(monkeypatch):
    from app.ai.models import AISeverity
    import warnings
    monkeypatch.setattr(AIService, '_ai_enabled', staticmethod(lambda: True))
    client = Mock()
    client.generate.return_value = json.dumps({'summary': 'An OOM kill was recorded.',
        'recommendations': [{'action': 'Invented action', 'risk': 'LOW', 'reason': 'fake'}]})
    result = AIService(client).diagnose(root_causes=[CAUSE])
    assert isinstance(result.severity, AISeverity)
    assert all(r.action != 'Invented action' for r in result.recommendations)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        result.model_dump(mode='json')


def test_http_401_is_observation_not_outage():
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    causes = []
    PodRootCauseService()._detect_authentication({}, [
        {'category': 'http', 'title': 'HTTP 401 responses observed', 'evidence': ['"GET / HTTP/1.1" 401 421']}
    ], causes)
    assert causes[0]['severity'] == 'info'
    assert causes[0]['confidence'] == 50
    assert 'do not establish' in causes[0]['description']


def test_numeric_substring_does_not_create_authentication_cause():
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    causes = []
    PodRootCauseService()._detect_authentication({}, [
        {'category': 'resources', 'title': 'Memory pressure', 'evidence': ['memory=401Mi']}
    ], causes)
    assert causes == []


def test_ollama_generation_limits(monkeypatch):
    from app.ai.ollama_client import OllamaClient
    post = Mock()
    post.return_value.json.return_value = {'response': '{"summary":"ok"}', 'done': True}
    monkeypatch.setattr('app.ai.ollama_client.httpx.post', post)
    OllamaClient().generate('small prompt')
    assert post.call_args.kwargs['timeout'] == 60
    assert post.call_args.kwargs['json']['options']['num_predict'] == 256


def test_placeholder_limitations_removed_real_gaps_preserved():
    result = AIService._parse_diagnosis({'summary': 'Observed HTTP 401 responses.',
        'limitations': ['uncertainties', 'N/A', 'Authentication configuration was not collected.',
                       'Authentication configuration was not collected.']})
    assert result.limitations == ['Authentication configuration was not collected.']
    assert '"limitations":[]' in AIService._system_prompt()


@pytest.mark.parametrize('category', ['probe', 'event'])
@pytest.mark.parametrize('message', [
    'Readiness probe failed: HTTP probe failed with statuscode: 403',
    'Readiness probe failed: dial tcp 10.0.0.2:80: connect: connection refused',
])
def test_probe_evidence_does_not_create_application_network_or_rbac_cause(category, message):
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    service = PodRootCauseService()
    issues = [{'category': category, 'title': 'Container health check is failing', 'evidence': [message]}]
    causes = []
    service._detect_probe_failure(issues, causes)
    service._detect_connection_refused(issues, causes)
    service._detect_authorization(issues, causes)
    assert causes
    assert all(c['category'] == 'health' for c in causes)


def test_independent_application_failure_survives_probe_filter():
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    service = PodRootCauseService()
    issues = [
        {'category': 'probe', 'title': 'Readiness probe failed', 'evidence': ['connection refused']},
        {'category': 'network', 'title': 'Dependency connection refused', 'evidence': ['database:5432 connection refused']},
        {'category': 'authorization', 'title': 'Permission denied', 'evidence': ['permission denied opening /data']},
    ]
    causes = []
    service._detect_connection_refused(issues, causes)
    service._detect_authorization(issues, causes)
    assert {c['category'] for c in causes} == {'network', 'authorization'}
    assert all('Readiness' not in ' '.join(c['evidence']) for c in causes)


def test_previous_oom_is_explicitly_historical_and_mixed_state_is_not():
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    service = PodRootCauseService()
    issue = {'category': 'resources', 'title': 'Container was OOMKilled',
             'evidence': ['last_state.terminated.reason=OOMKilled']}
    causes = []
    service._detect_oom([issue], causes)
    assert causes[0]['title'] == 'Previous container OOM kill recorded'
    assert 'does not establish a current outage' in causes[0]['description']
    issue['evidence'].append('state.terminated.reason=OOMKilled')
    causes = []
    service._detect_oom([issue], causes)
    assert causes[0]['title'] == 'Container exceeded available memory'


@pytest.mark.parametrize('line,expected', [
    ('2026-09-23 10:29:15.217" INFO [ThreadPoolTaskExecutorConfig] Initializing threadpool with the following config corePoolSize : 250 , maxPoolSize 500 , queueCapacity 2000 , timeout 60', False),
    ('INFO request timeout configured to 60 seconds', False),
    ('INFO connection timeout=60', False),
    ('ERROR request timed out after 60 seconds', True),
    ('java.net.SocketTimeoutException: Read timed out', True),
    ('ERROR connect ETIMEDOUT', True),
])
def test_timeout_requires_failure_evidence(line, expected):
    from app.kubernetes.services.investigation.diagnostics.pod_diagnostics import PodDiagnosticsService
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    diagnostics = PodDiagnosticsService().analyze({'logs': {'containers': {'app': {'logs': [line]}}}})
    roots = PodRootCauseService().analyze({}, diagnostics)['root_causes']
    assert any('timeout' in cause['title'].lower() for cause in roots) is expected


def test_timeout_correlation_rejects_old_false_positive_and_keeps_gateway():
    from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService
    service = PodRootCauseService()
    causes = []
    service._detect_timeout([{'category': 'network', 'title': 'Application timeout detected',
        'evidence': ['INFO initializing timeout 60']}], causes)
    assert causes == []
    service._detect_timeout([{'category': 'http', 'title': 'HTTP gateway timeout responses detected',
        'evidence': ['"GET / HTTP/1.1" 504 123']}], causes)
    assert len(causes) == 1
