from types import SimpleNamespace
import pytest
from app.kubernetes.services import deployment_yaml_service as module

YAML = '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: default
spec:
  selector:
    matchLabels: {app: api}
  template:
    metadata:
      labels: {app: api}
    spec:
      containers:
        - name: api
          image: example:v1
'''


def test_created_backup_can_be_read_and_restored(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'BACKUP_ROOT', tmp_path)
    calls = []
    class Client:
        def current_context(self): return SimpleNamespace(stdout='test-context')
        def get_deployment_yaml(self, *args): return SimpleNamespace(stdout=YAML)
        def validate_deployment_yaml(self, path):
            calls.append('validate')
            return SimpleNamespace(stdout='validated')
        def apply_deployment_yaml(self, path):
            calls.append('apply')
            return SimpleNamespace(stdout='applied')
        def rollout_status(self, *args):
            calls.append('rollout')
            return SimpleNamespace(stdout='rolled out')
    service = module.DeploymentYamlService(Client())
    backup = service._create_backup('default', 'api', YAML, 'test')
    assert service.get_backup('default', 'api', backup['id'])['yaml'] == YAML
    result = service.restore('default', 'api', backup['id'])
    assert result['success'] is True
    assert 'Rollback restored' in result['message']
    assert result['restored_backup_id'] == backup['id']
    assert service.get_backup('default', 'api', result['recovery_backup_id'])['yaml'] == YAML
    assert calls == ['validate', 'apply', 'rollout']


@pytest.mark.parametrize('backup_id', ['../20260923T064501165996Z', '20260923T064501165996Z/other', '', '20260923064501165996Z'])
def test_backup_id_rejects_invalid_paths(backup_id):
    with pytest.raises(ValueError, match='Invalid backup ID'):
        module.DeploymentYamlService._validate_backup_id(backup_id)


@pytest.mark.parametrize('operation', ['apply', 'restore'])
def test_rollout_timeout_preserves_applied_result(tmp_path, monkeypatch, operation):
    from app.kubernetes.exceptions import KubectlTimeoutError
    monkeypatch.setattr(module, 'BACKUP_ROOT', tmp_path)
    calls = []
    class Client:
        def current_context(self): return SimpleNamespace(stdout='test')
        def get_deployment_yaml(self, *args): return SimpleNamespace(stdout=YAML)
        def validate_deployment_yaml(self, path): return SimpleNamespace(stdout='validated')
        def apply_deployment_yaml(self, path):
            calls.append('apply')
            return SimpleNamespace(stdout='deployment configured')
        def rollout_status(self, *args): raise KubectlTimeoutError('rollout timed out')
    service = module.DeploymentYamlService(Client())
    if operation == 'apply':
        result = service.apply('default', 'api', YAML)
        backup_id = result['backup_id']
    else:
        backup = service._create_backup('default', 'api', YAML, 'test')
        result = service.restore('default', 'api', backup['id'])
        backup_id = result['recovery_backup_id']
    assert calls == ['apply']
    assert result['applied'] is True
    assert result['success'] is False
    assert result['rollout_status'] == 'unconfirmed'
    assert ('YAML applied' if operation == 'apply' else 'rollback rollout not confirmed') in result['message']
    assert service.get_backup('default', 'api', backup_id)['yaml'] == YAML


def test_rollout_process_outlives_kubectl_deadline(monkeypatch):
    import subprocess
    from app.kubernetes.client import KubectlClient
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs['timeout']))
        return SimpleNamespace(stdout='rolled out', stderr='', returncode=0)
    monkeypatch.setattr(subprocess, 'run', run)
    KubectlClient().rollout_status('default', 'api')
    assert '--timeout=60s' in calls[0][0]
    assert calls[0][1] > 60
