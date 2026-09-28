from types import SimpleNamespace
import pytest
from app.kubernetes.client import KubectlClient
from app.kubernetes.exceptions import InvalidKubectlArgumentError
from app.kubernetes.services.pod_service import PodService
from app.schemas.log import PodLogsResponse

class Executor:
    def execute(self,args,**kw):
        self.args=args
        return SimpleNamespace(stdout='2026-09-24T22:30:00Z failed request\n')


def test_absolute_log_start_and_container_flags():
    ex=Executor(); client=KubectlClient(executor=ex)
    client.logs('pod','default',container='init-copy',previous=True,tail=100000,since_time='2026-09-25T04:00:00+05:30',timestamps=True)
    assert '--since-time' in ex.args and '2026-09-25T04:00:00+05:30' in ex.args
    assert '--previous' in ex.args and '--timestamps' in ex.args and '100000' in ex.args
    assert '--since' not in ex.args

@pytest.mark.parametrize('stamp',['2026-09-25T04:00:00','--follow','2026-02-30T04:00:00Z'])
def test_bad_log_timestamps_rejected(stamp):
    with pytest.raises(InvalidKubectlArgumentError): KubectlClient(Executor()).logs('pod','default',since_time=stamp)


def test_relative_and_absolute_time_cannot_be_combined():
    with pytest.raises(InvalidKubectlArgumentError): KubectlClient(Executor()).logs('pod','default',since='24h',since_time='2026-09-24T00:00:00Z')


def test_api_model_preserves_unavailable_previous_logs():
    class Client:
        def logs(self,**kw):
            assert kw['since_time']=='2026-09-24T00:00:00Z'
            raise RuntimeError('previous container not found')
    response=PodService(client=Client()).get_logs('default','pod',previous=True,since_time='2026-09-24T00:00:00Z')
    model=PodLogsResponse.model_validate(response)
    assert model.available is False and model.previous is True and 'not found' in model.message


def test_log_error_preserves_actionable_kubectl_stderr():
    from app.kubernetes.exceptions import CommandExecutionError
    class Client:
        def logs(self,**kw):
            raise CommandExecutionError('kubectl command failed.','kubectl logs pod', 'previous terminated container not found',1)
    response=PodService(client=Client()).get_logs('default','pod',previous=True)
    assert 'previous terminated container not found' in response['message']
    assert response['available'] is False
