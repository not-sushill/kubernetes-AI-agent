import hashlib
import json
from types import SimpleNamespace
from datetime import datetime, timezone
from copy import deepcopy
import pytest
from pydantic import ValidationError
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.base import Base
from app.operations.models import OperationRecord
from app.operations.archive import ArchiveQuery, logql, query_archive
from app.operations.evidence import incident_timeline, relationships
from app.operations.security import TeamAccessMiddleware, required_role, configured_users
from app.operations.router import RunbookBody
from app.operations.verification import verify
from app.operations.jobs import create_job
from app.investigations.models import InvestigationCreate
from tests.test_ai_fixes import setup, propose

@pytest.mark.parametrize('role,allowed',[('viewer',False),('operator',False),('approver',True),('admin',True)])
def test_apply_and_terminal_permissions(monkeypatch,role,allowed):
    token='a-long-random-token'
    monkeypatch.setenv('TEAM_USERS_JSON',json.dumps([{'name':'tester','role':role,'token_sha256':hashlib.sha256(token.encode()).hexdigest()}]))
    monkeypatch.setattr('app.operations.security.audit',lambda *args:None)
    app=FastAPI();app.add_middleware(TeamAccessMiddleware)
    @app.post('/api/v1/fixes/id/apply')
    def apply():return {'sent':True}
    @app.post('/api/kubernetes/container-access/terminal')
    def terminal():return {'sent':True}
    with TestClient(app) as c:
        for path in ['/api/v1/fixes/id/apply','/api/kubernetes/container-access/terminal']:
            assert c.post(path,headers={'X-API-Key':token}).status_code==(200 if allowed else 403)
            assert c.post(path).status_code==401

@pytest.mark.parametrize('path',['/api/v1/operations/jobs','/api/v1/operations/archive','/api/v1/fixes/id/diagnostic-runs','/api/v1/operations/runbooks/id/run','/api/v1/investigations/id/fixes'])
def test_operator_read_only_workflows(path):assert required_role('POST',path)==1

def test_unknown_mutation_fail_closed():
    assert required_role('POST','/api/new/mutation')==2
    assert required_role('GET','/api/v1/operations/audit')==3


def test_archive_exact_selectors_and_timezone(monkeypatch):
    q=ArchiveQuery(cluster='a',namespace='default',pod='pod"} |= "x',text='" | drop x',start='2026-09-25T08:30:00+05:30',end='2026-09-25T09:00:00+05:30')
    assert q.start.astimezone(timezone.utc).hour==3
    assert json.dumps(q.pod) in logql(q) and logql(q).endswith(json.dumps(q.text))
    monkeypatch.delenv('LOKI_URL',raising=False)
    with pytest.raises(HTTPException) as e:query_archive(q)
    assert e.value.status_code==503

@pytest.mark.parametrize('start,end',[('2026-09-25T08:30:00','2026-09-25T09:30:00'),('2026-09-25T08:30:00Z','2026-09-24T08:30:00Z'),('2026-09-01T08:30:00Z','2026-09-25T08:30:00Z')])
def test_archive_bounds(start,end):
    with pytest.raises(ValidationError):ArchiveQuery(cluster='x',namespace='y',start=start,end=end)

def test_runbooks_cannot_embed_commands():
    with pytest.raises(ValidationError):RunbookBody(name='Unsafe',checks=['kubectl delete pod'])
    with pytest.raises(ValidationError):RunbookBody(name='Repeat',checks=['pod_status','pod_status'])

def test_relationships_are_uid_and_namespace_scoped():
    items=[{'kind':'Deployment','metadata':{'uid':'d','name':'demo','namespace':'a'}},
      {'kind':'ReplicaSet','metadata':{'uid':'r','name':'rs','namespace':'a','ownerReferences':[{'uid':'d'}]}},
      {'kind':'Pod','metadata':{'uid':'p','name':'pod','namespace':'a','labels':{'app':'demo'},'ownerReferences':[{'uid':'r'}]},'spec':{'nodeName':'node'}},
      {'kind':'Pod','metadata':{'uid':'other','name':'other','namespace':'b','labels':{'app':'demo'}}},
      {'kind':'Service','metadata':{'uid':'s','name':'svc','namespace':'a'},'spec':{'selector':{'app':'demo'}}}]
    data=relationships(items)
    assert {'from':'s','to':'p','relation':'selects'} in data['edges']
    assert not any(e['to']=='other' for e in data['edges'])
    assert {'from':'p','to':'node:node','relation':'scheduled on'} in data['edges']

def test_timeline_uses_actual_timestamps_not_guessed_times():
    record=SimpleNamespace(status='COMPLETED',resource_name='demo',created_at=datetime(2026,9,25),evidence={'pod':{'data':{'name':'p','age':'3d','containers':[{'name':'c','last_state':{'terminated':{'reason':'OOMKilled','finishedAt':'2026-09-23T08:00:00Z'}}}]}},'events':{'data':{'events':[{'reason':'Unhealthy','last_timestamp':'2026-09-24T03:00:00Z','involved_object':{'name':'p'}}]}}})
    result=incident_timeline(record)
    assert len(result['items'])==3 and result['items'][0]['title']=='OOMKilled'
    assert result['items'][1]['resource']=='p'


def test_queue_persists_context_and_request_without_execution():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        row=create_job(db,InvestigationCreate(namespace='default',resource_type='pod',resource_name='demo'),'cluster-a','tester')
        ident=row.id
    with Session(engine) as db:
        row=db.get(OperationRecord,ident)
        assert row.state=='QUEUED' and row.payload['context']=='cluster-a' and row.payload['actor']=='tester'
    engine.dispose()


def test_verification_rejects_unapplied_and_changed_target(setup):
    p=propose(setup);s,_,ex,_=setup
    with pytest.raises(HTTPException):verify(s.db,p['id'],ex)
    s.validate(p['id']);s.mutate(p['id'],p['confirmation']);writes=ex.writes
    ex.obj['metadata']['uid']='replacement'
    result=verify(s.db,p['id'],ex)
    assert result['state']=='INCOMPLETE' and ex.writes==writes
    assert result['checks'][0]['passed'] is False


def test_verification_samples_do_not_expose_log_content(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id']);s.mutate(p['id'],p['confirmation']);writes=ex.writes
    original=ex.execute
    def execute(args,**kwargs):
        if 'logs' in args:return SimpleNamespace(stdout='ERROR secret-password\n')
        if 'replicasets' in args:data={'items':[{'metadata':{'uid':'rs','ownerReferences':[{'uid':'uid1','controller':True}]}}]}
        elif 'pods' in args:data={'items':[{'metadata':{'name':'p','uid':'p','labels':{},'ownerReferences':[{'uid':'rs','controller':True}]},'spec':{'containers':[{'name':'web'}]},'status':{'conditions':[{'type':'Ready','status':'True'}]}}]}
        elif 'services' in args or 'endpointslices' in args:data={'items':[]}
        else:return original(args,**kwargs)
        return SimpleNamespace(stdout=json.dumps(data))
    ex.execute=execute
    result=verify(s.db,p['id'],ex)
    assert result['state']=='NEEDS_REVIEW' and 'secret-password' not in json.dumps(result) and ex.writes==writes

def test_worker_uses_saved_cluster_and_completes_after_ui_leaves(monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from app.operations import jobs
    from app.kubernetes.executor import bound_context
    engine=create_engine('sqlite://');Base.metadata.create_all(engine);factory=sessionmaker(bind=engine,expire_on_commit=False)
    monkeypatch.setattr(jobs,'SessionLocal',factory)
    with factory() as db:
        ident=jobs.create_job(db,InvestigationCreate(namespace='default',resource_type='pod',resource_name='demo'),'cluster-fixed','user').id
    class Service:
        def __init__(self,db,cluster_service):
            assert cluster_service.context=='cluster-fixed'
            self._build_analysis=lambda evidence:None
        def create(self,request):
            assert bound_context.get()=='cluster-fixed'
            self._build_analysis(None)
            return SimpleNamespace(id='result-id',status=SimpleNamespace(value='COMPLETED'))
    monkeypatch.setattr(jobs,'InvestigationService',Service)
    assert jobs.process_one() is True and jobs.process_one() is False
    with factory() as db:
        row=db.get(OperationRecord,ident)
        assert row.state=='COMPLETED' and row.payload['investigation_id']=='result-id'
    assert bound_context.get() is None
    engine.dispose()


def test_archive_response_is_sorted_and_limited(monkeypatch):
    from app.operations import archive
    monkeypatch.setenv('LOKI_URL','https://logs.example')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_bytes(self):yield json.dumps({'status':'success','data':{'resultType':'streams','result':[{'stream':{'pod':'a'},'values':[['2','second'],['1','first']]}]}}).encode()
    class Client:
        def __init__(self,**kwargs):assert kwargs['follow_redirects'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def stream(self,method,url,params,headers):
            assert method=='GET' and params['direction']=='forward' and params['limit']==1
            return Response()
    monkeypatch.setattr(archive.httpx,'Client',Client)
    result=archive.query_archive(ArchiveQuery(cluster='a',namespace='b',start='2026-09-25T00:00:00Z',end='2026-09-25T01:00:00Z',limit=1))
    assert result['rows'][0]['line']=='first' and result['limit_reached']

def test_assessment_history_has_no_fabricated_deletion_diff(setup):
    from app.operations.router import changes
    from app.remediation.models import ProposeRequest
    s,inv,ex,ai=setup
    ai.generate=lambda *args,**kwargs:json.dumps({'decision':'needs_information','explanation':'Need verified facts before proposing a change.','evidence_ids':[0],'checks':['Verify health endpoint.'],'changes':[]})
    p=s.propose(inv.id,ProposeRequest(deployment='demo',objective='Assess health without making changes.',assessment_only=True))
    result=changes(inv.id,s.db)
    assert result[0]['id']==p['id'] and result[0]['diff']==''


def test_notification_unknown_blocks_duplicate_send(monkeypatch):
    from app.operations import router
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    monkeypatch.setenv('ALERT_WEBHOOK_URL','https://notifications.example/inbox')
    calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,json):calls.append(json);raise TimeoutError()
    monkeypatch.setattr(router.httpx,'Client',Client)
    with Session(engine,expire_on_commit=False) as db:
        row=OperationRecord(kind='alert',state='OPEN',payload={'title':'Failure','severity':'high','namespace':'a','resource':'b','investigation_id':'i'});db.add(row);db.commit()
        with pytest.raises(HTTPException) as exc:router.notify(row.id,db)
        assert exc.value.status_code==502 and row.state=='DELIVERY_UNKNOWN'
        with pytest.raises(HTTPException) as exc:router.notify(row.id,db)
        assert exc.value.status_code==409 and len(calls)==1
    engine.dispose()
