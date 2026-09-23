from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.investigations.models import InvestigationEvidence, InvestigationSection
from app.investigations.router import get_investigation_service
from app.investigations.service import InvestigationService
from app.main import app
from tests.unit.test_investigations import FakeClusterService


class EvidenceCollector:
    def collect(self, request):
        evidence = {name: InvestigationSection.collected([]) for name in (
            'namespace', 'pod', 'deployment', 'replicaset', 'node', 'events', 'logs',
            'services', 'pvc', 'metrics', 'endpoints', 'network_policies', 'resource_quotas')}
        evidence['namespace'] = InvestigationSection.collected({'name': request.namespace, 'found': True})
        evidence['pod'] = InvestigationSection.collected({'name': request.resource_name,
            'containers': [{'name': 'app', 'state': {'waiting': {'reason': 'CrashLoopBackOff'}},
                'last_state': {'terminated': {'reason': 'OOMKilled', 'exitCode': 137}}}]})
        evidence['logs'] = InvestigationSection.collected({'containers': {'app': {'logs': []}}})
        return InvestigationEvidence(**evidence)


def test_create_get_history_filters_and_reopen(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'history.db'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def service():
        with sessions() as db:
            yield InvestigationService(db, collector=EvidenceCollector(), cluster_service=FakeClusterService())
    app.dependency_overrides[get_investigation_service] = service
    try:
        with TestClient(app) as client:
            payload = {'namespace': 'default', 'resource_type': 'pod', 'resource_name': 'oom-test'}
            response = client.post('/api/v1/investigations', json=payload)
            assert response.status_code == 201, response.text
            body = response.json()
            cause = body['analysis']['root_causes'][0]
            assert cause['category'] == 'resources' and cause['confidence'] == 85
            assert body['status'] == 'COMPLETED'
            identifier = body['id']
            assert client.get('/api/v1/investigations/' + identifier).json()['analysis'] == body['analysis']
            listed = client.get('/api/v1/investigations', params={'namespace': 'default', 'resource_type': 'pod', 'status': 'COMPLETED', 'search': 'oom-test', 'page_size': 1}).json()
            assert listed['total'] == 1 and listed['items'][0]['id'] == identifier
            assert client.get('/api/v1/investigations/not-present').status_code == 404
            assert client.get('/api/v1/investigations?page=0').status_code == 422
            assert client.post('/api/v1/investigations', json={'namespace': 'default', 'resource_type': 'service'}).status_code == 422
        engine.dispose()
        # Reopen the physical file with a new engine/session.
        another = create_engine('sqlite:///' + str(tmp_path / 'history.db'))
        with sessionmaker(bind=another)() as db:
            loaded = InvestigationService(db, collector=EvidenceCollector()).get(identifier)
            assert loaded.analysis.root_causes[0]['evidence'] == cause['evidence']
        another.dispose()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_ollama_timeout_does_not_lose_persisted_investigation(tmp_path, monkeypatch):
    from app.ai.service import AIService
    from app.ai.ollama_client import OllamaClient
    monkeypatch.setattr(AIService, '_ai_enabled', staticmethod(lambda: True))
    def timeout(*args, **kwargs):
        raise TimeoutError('Ollama timeout')
    monkeypatch.setattr(OllamaClient, 'generate', timeout)
    engine = create_engine('sqlite:///' + str(tmp_path / 'fallback.db'))
    Base.metadata.create_all(engine)
    from app.investigations.models import InvestigationCreate
    with sessionmaker(bind=engine)() as db:
        service = InvestigationService(db, collector=EvidenceCollector(), cluster_service=FakeClusterService())
        created = service.create(InvestigationCreate(namespace='default', resource_type='pod', resource_name='oom'))
        loaded = service.get(created.id)
        assert loaded.analysis.ai.severity == 'CRITICAL'
        assert loaded.analysis.ai.confidence == 85
        assert loaded.analysis.ai.limitations
    engine.dispose()


def test_primary_failure_marks_run_failed(tmp_path):
    class FailedCollector(EvidenceCollector):
        def collect(self, request):
            result = super().collect(request)
            result.pod = InvestigationSection.failed('Pod not found')
            return result
    engine = create_engine('sqlite:///' + str(tmp_path / 'failed.db'))
    Base.metadata.create_all(engine)
    from app.investigations.models import InvestigationCreate
    with sessionmaker(bind=engine)() as db:
        service = InvestigationService(db, collector=FailedCollector(), cluster_service=FakeClusterService())
        created = service.create(InvestigationCreate(namespace='default', resource_type='pod', resource_name='missing'))
        assert created.status == 'FAILED'
        assert not created.analysis.root_causes
    engine.dispose()


def test_default_context_path_resolves_and_persists(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.kubernetes.executor import KubectlExecutor
    from app.investigations.models import InvestigationCreate
    calls = []
    def execute(self, args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout='test-context\n')
    monkeypatch.setattr(KubectlExecutor, 'execute', execute)
    engine = create_engine('sqlite:///' + str(tmp_path / 'context.db'))
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        service = InvestigationService(db, collector=EvidenceCollector())
        created = service.create(InvestigationCreate(namespace='default', resource_type='pod', resource_name='oom'))
        assert service.list().items[0].cluster == 'test-context'
        assert service.get(created.id).analysis.root_causes[0]['category'] == 'resources'
        assert calls == [['config', 'current-context']]
    engine.dispose()


def test_default_context_failure_preserves_fallback(monkeypatch):
    from app.kubernetes.executor import KubectlExecutor
    from app.kubernetes.exceptions import KubectlNotFoundError
    def execute(self, args, **kwargs):
        raise KubectlNotFoundError('kubectl not found')
    monkeypatch.setattr(KubectlExecutor, 'execute', execute)
    service = InvestigationService(None, collector=EvidenceCollector())
    assert service._cluster_context() == 'unknown'


def test_local_console_served_without_changing_root_api():
    with TestClient(app) as client:
        response = client.get('/console')
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
        assert 'Kubernetes Investigation Console' in response.text
        assert client.get('/').json()['status'] == 'running'


def test_node_detail_route_preserves_enrichment():
    from app.api.routes.kubernetes.nodes import get_node_service
    class FakeNode:
        def get_node_detail(self, name):
            return dict(name=name, status="True", roles="worker", version="v1",
                internal_ip="10.0.0.1", os_image="Linux", kernel_version="k",
                container_runtime="containerd", age="now", labels={}, annotations={},
                capacity={}, allocatable={}, conditions=[], metrics={"available": False},
                health_score=80, events=[{"reason": "Test"}], yaml="kind: Node",
                provider_id="provider", pod_cidr="10.1.0.0/16", unschedulable=False)
    app.dependency_overrides[get_node_service] = lambda: FakeNode()
    try:
        with TestClient(app) as client:
            response = client.get('/api/kubernetes/nodes/node-a')
            assert response.status_code == 200
            data = response.json()
            assert data['health_score'] == 80
            assert data['metrics']['available'] is False
            assert data['events'][0]['reason'] == 'Test'
            assert data['yaml'] == 'kind: Node'
    finally:
        app.dependency_overrides.pop(get_node_service, None)


def test_service_events_are_filtered_by_kind_and_name():
    from types import SimpleNamespace
    import json
    from app.kubernetes.services.service_service import ServiceService
    items = [
        {"involvedObject": {"kind": "Service", "name": "api"}, "reason": "Selected"},
        {"involvedObject": {"kind": "Pod", "name": "api"}, "reason": "WrongKind"},
        {"involvedObject": {"kind": "Service", "name": "other"}, "reason": "WrongName"},
    ]
    client = SimpleNamespace(get_namespace_events=lambda ns: SimpleNamespace(stdout=json.dumps({"items": items})))
    result = ServiceService(client).get_events("default", "api")
    assert result["total_events"] == 1
    assert result["events"][0]["reason"] == "Selected"


def test_node_events_execute_single_kubectl(monkeypatch):
    import subprocess
    from types import SimpleNamespace
    from app.kubernetes.services.node_service import NodeService
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout='{"items":[{"reason":"Ready","message":"ready"}]}', stderr='')
    monkeypatch.setattr(subprocess, 'run', run)
    events = NodeService().get_events('node-a')
    assert commands[0][:3] == ['kubectl', 'get', 'events']
    assert 'involvedObject.kind=Node,involvedObject.name=node-a' in commands[0]
    assert events[0]['reason'] == 'Ready'


def test_deployment_mutations_require_matching_confirmation():
    from app.api.routes.kubernetes.deployments import get_deployment_yaml_service
    calls = []
    class FakeService:
        def apply(self, *args):
            calls.append(('apply', args))
            return dict(success=True, deployment='api', namespace='default', backup_id='b', apply_output='', rollout_output='')
        def restore(self, *args):
            calls.append(('restore', args))
            return dict(success=True, deployment='api', namespace='default', restored_backup_id='b', recovery_backup_id='r', apply_output='', rollout_output='')
    app.dependency_overrides[get_deployment_yaml_service] = lambda: FakeService()
    try:
        with TestClient(app) as client:
            apply = '/api/kubernetes/deployments/default/api/yaml/apply'
            restore = '/api/kubernetes/deployments/default/api/backups/b/restore'
            assert client.post(apply, json={'yaml': 'test'}).status_code == 422
            assert client.post(apply, json={'yaml': 'test', 'confirmation': 'APPLY default/other'}).status_code == 400
            assert client.post(restore, json={}).status_code == 422
            assert client.post(restore, json={'confirmation': 'RESTORE default/api wrong'}).status_code == 400
            assert calls == []
            assert client.post(apply, json={'yaml': 'test', 'confirmation': 'APPLY default/api'}).status_code == 200
            assert client.post(restore, json={'confirmation': 'RESTORE default/api b'}).status_code == 200
            assert [x[0] for x in calls] == ['apply', 'restore']
    finally:
        app.dependency_overrides.pop(get_deployment_yaml_service, None)
