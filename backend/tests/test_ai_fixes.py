import json
from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.base import Base
from app.models.investigation import Investigation
from app.remediation.models import ProposeRequest, ModelPlan
from app.remediation.service import FixService, apply_changes, editable

BASE = {'replicas':1,'selector':{'matchLabels':{'app':'demo'}},'template':{'metadata':{'labels':{'app':'demo'}},'spec':{'containers':[{'name':'web','image':'demo:v1','env':[{'name':'TOKEN','value':'secret-value'}],'readinessProbe':{'httpGet':{'path':'/','port':80,'httpHeaders':[{'name':'Authorization','value':'secret-header'}]},'periodSeconds':10}}]}}}
PLAN = {'decision':'propose','explanation':'Use the health path verified by the operator for the failing probe.','evidence_ids':[0],'checks':['Verify authenticated traffic after rollout.'],'changes':[{'path':'/spec/template/spec/containers/0/readinessProbe/httpGet/path','value':'/health'}]}

class Executor:
    def __init__(self):
        self.obj={'metadata':{'uid':'uid1','resourceVersion':'1'},'spec':deepcopy(BASE)}
        self.calls=[]; self.writes=0; self.timeout=False; self.rollout_fail=False; self.admission=False
    def execute(self,args,**kw):
        self.calls.append(args)
        assert args[:4]==['--context','cluster-a','-n','default']
        if 'patch' in args:
            with open(args[args.index('--patch-file')+1]) as f: ops=json.load(f)
            assert ops[0]['value']==self.obj['metadata']['uid']
            assert ops[1]['value']==self.obj['metadata']['resourceVersion']
            out=deepcopy(self.obj); out['spec']=ops[2]['value']
            if self.admission: out['spec']['replicas']=7
            if '--dry-run=server' not in args:
                self.writes+=1
                if self.timeout: raise TimeoutError('timeout')
                self.obj=out
            return SimpleNamespace(stdout=json.dumps(out))
        if 'rollout' in args and self.rollout_fail: raise TimeoutError('rollout timeout')
        return SimpleNamespace(stdout=json.dumps(self.obj))

class AI:
    def generate(self,prompt,**kw):
        self.prompt=prompt
        return json.dumps(PLAN)

@pytest.fixture
def setup():
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine,expire_on_commit=False) as db:
        inv=Investigation(cluster='cluster-a',namespace='default',resource_type='deployment',resource_name='demo',status='COMPLETED',evidence={'analysis':{'root_causes':[{'title':'Readiness probe failure','evidence':['HTTP 403']}]}})
        db.add(inv);db.commit()
        ex=Executor();ai=AI();s=FixService(db,ex,ai)
        yield s,inv,ex,ai
    engine.dispose()

def propose(setup):
    s,inv,_,_=setup
    return s.propose(inv.id,ProposeRequest(deployment='demo',objective='The operator verified /health is the unauthenticated readiness route.'))

def test_generate_is_read_only_and_preserves_other_fields(setup):
    p=propose(setup);s,inv,ex,ai=setup
    assert p['state']=='PROPOSED' and ex.writes==0
    assert 'secret-value' not in ai.prompt and 'secret-header' not in ai.prompt
    assert '/health' in p['diff'] and 'secret-value' not in p['diff']
    assert s.load(p['id']).payload['after']['template']['spec']['containers'][0]['env']==BASE['template']['spec']['containers'][0]['env']
    assert s.list(inv.id)[0]['id']==p['id']
    assert 'before' not in p


def test_validate_apply_and_explicit_rollback(setup):
    p=propose(setup);s,_,ex,_=setup
    p=s.validate(p['id']);assert p['state']=='VALIDATED' and ex.writes==0
    p=s.mutate(p['id'],p['confirmation']);assert p['state']=='APPLIED' and ex.writes==1
    assert s.load(p['id']).payload['before']==BASE
    p=s.mutate(p['id'],p['rollback_confirmation'],rollback=True)
    assert p['state']=='ROLLED_BACK' and ex.obj['spec']==BASE and ex.writes==2
    assert len(p['audit'])==6

@pytest.mark.parametrize('text',['123','APPLY default/demo',''])
def test_wrong_confirmation_never_mutates(setup,text):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id'])
    with pytest.raises(HTTPException): s.mutate(p['id'],text)
    assert ex.writes==0


def test_validation_required(setup):
    p=propose(setup)
    with pytest.raises(HTTPException): setup[0].mutate(p['id'],p['confirmation'])
    assert setup[2].writes==0

@pytest.mark.parametrize('drift',['uid','spec'])
def test_stale_approval_blocks_write(setup,drift):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id'])
    if drift=='uid': ex.obj['metadata']['uid']='replaced'
    else: ex.obj['spec']['replicas']=2
    with pytest.raises(HTTPException): s.mutate(p['id'],p['confirmation'])
    assert ex.writes==0


def test_status_only_resourceversion_change_is_safe(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id'])
    ex.obj['metadata']['resourceVersion']='new-status-version'
    assert s.mutate(p['id'],p['confirmation'])['state']=='APPLIED'


def test_duplicate_apply_blocked(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id']);s.mutate(p['id'],p['confirmation'])
    with pytest.raises(HTTPException): s.mutate(p['id'],p['confirmation'])
    assert ex.writes==1


def test_apply_timeout_not_reported_success_or_retried(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id']);ex.timeout=True
    assert s.mutate(p['id'],p['confirmation'])['state']=='OUTCOME_UNKNOWN'
    with pytest.raises(HTTPException): s.mutate(p['id'],p['confirmation'])
    assert ex.writes==1


def test_rollout_timeout_keeps_rollback_available(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id']);ex.rollout_fail=True
    assert s.mutate(p['id'],p['confirmation'])['state']=='APPLIED_UNCONFIRMED'
    assert s.mutate(p['id'],p['rollback_confirmation'],rollback=True)['state']=='ROLLED_BACK_UNCONFIRMED'


def test_rollback_rejects_later_operator_change(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id']);s.mutate(p['id'],p['confirmation']);ex.obj['spec']['replicas']=3
    with pytest.raises(HTTPException): s.mutate(p['id'],p['rollback_confirmation'],rollback=True)
    assert ex.writes==1


def test_admission_unseen_changes_blocked(setup):
    p=propose(setup);s,_,ex,_=setup;ex.admission=True
    with pytest.raises(HTTPException): s.validate(p['id'])
    assert ex.writes==0

@pytest.mark.parametrize('path,value',[
    ('/spec/template/spec/containers/0/command',['sh']),
    ('/spec/template/spec/containers/0/securityContext/privileged',True),
    ('/spec/template/spec/containers/0/readinessProbe',None),
    ('/spec/replicas',0),
    ('/spec/template/spec/containers/2/image','other:v1'),
    ('/spec/template/spec/containers/0/readinessProbe/httpGet/httpHeaders',[]),
    ('/spec/template/spec/containers/0/resources/limits/memory','0Mi'),
])
def test_model_cannot_escape_supported_changes(path,value):
    plan=ModelPlan.model_validate({**PLAN,'changes':[{'path':path,'value':value}]})
    with pytest.raises(HTTPException): apply_changes(BASE,plan.changes)


def test_needs_information_does_not_create_mutable_proposal(setup):
    s,_,ex,ai=setup
    ai.generate=lambda *a,**kw: json.dumps({**PLAN,'decision':'needs_information','changes':[]})
    p=propose(setup);assert p['state']=='NEEDS_INFORMATION'
    with pytest.raises(HTTPException): s.validate(p['id'])
    assert ex.writes==0


def test_invalid_ai_response_never_falls_back_to_a_fix(setup):
    setup[3].generate=lambda *a,**kw: '{}'
    with pytest.raises(HTTPException) as error: propose(setup)
    assert error.value.status_code==502 and setup[2].writes==0


def test_target_must_belong_to_investigation(setup):
    s,inv,ex,_=setup
    with pytest.raises(HTTPException): s.propose(inv.id,ProposeRequest(deployment='other',objective='Please fix the readiness path'))
    assert not ex.calls


def test_expired_validation_requires_new_dryrun(setup):
    p=propose(setup);s,_,ex,_=setup;s.validate(p['id'])
    row=s.load(p['id']);row.payload={**row.payload,'validated_at':'2020-01-01T00:00:00+00:00'};s.db.commit()
    with pytest.raises(HTTPException): s.mutate(p['id'],p['confirmation'])
    assert ex.writes==0


def test_http_routes_enforce_origin_schema_and_persisted_listing(setup):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.remediation.router import router, service
    s,inv,ex,_=setup
    # Use the same-thread service for the test route dependency; SQLite fixture
    # is thread-bound, so test only requests rejected before database access here.
    app=FastAPI();app.include_router(router,prefix='/api');app.dependency_overrides[service]=lambda:s
    with TestClient(app) as client:
        r=client.post('/api/v1/fixes/example/validate',headers={'Origin':'https://untrusted.example'})
        assert r.status_code==403
        r=client.post('/api/v1/fixes/example/apply',json={'confirmation':'123','yaml':'injected'})
        assert r.status_code==422
    assert ex.writes==0


def test_proposal_survives_new_service_session(setup):
    p=propose(setup);s,inv,ex,ai=setup
    with Session(s.db.get_bind()) as new_db:
        restored=FixService(new_db,ex,ai).list(inv.id)
        assert restored[0]['id']==p['id'] and restored[0]['diff']==p['diff']


def test_init_image_change_preserves_commands_mounts_and_main_container():
    spec=deepcopy(BASE)
    spec['template']['spec']['initContainers']=[{'name':'init-copy-folders','image':'old:v1','command':['sh','-c','cp -r /seed /data'],'volumeMounts':[{'name':'data','mountPath':'/data'}]}]
    plan=ModelPlan.model_validate({**PLAN,'changes':[{'path':'/spec/template/spec/initContainers/0/image','value':'registry.example/team/seed:v2'}]})
    changed=apply_changes(spec,plan.changes)
    assert changed['template']['spec']['containers']==spec['template']['spec']['containers']
    init=changed['template']['spec']['initContainers'][0]
    assert init['image']=='registry.example/team/seed:v2' and init['command']==spec['template']['spec']['initContainers'][0]['command']
    assert 'command' not in editable(spec)['template']['spec']['initContainers'][0]
    bad=ModelPlan.model_validate({**PLAN,'changes':[{'path':'/spec/template/spec/initContainers/0/command','value':['sh']}]})
    with pytest.raises(HTTPException): apply_changes(spec,bad.changes)


def test_pod_target_resolves_live_controller_chain_and_blocks_recreated_pod(setup):
    s,inv,ex,_=setup
    inv.resource_type='pod';inv.resource_name='demo-pod'
    inv.evidence={**inv.evidence,'pod':{'data':[{'name':'demo-pod','uid':'pod-uid'}]}}
    s.db.commit()
    real=ex.execute
    pod={'metadata':{'uid':'pod-uid','ownerReferences':[{'controller':True,'kind':'ReplicaSet','name':'demo-rs','uid':'rs-uid'}]}}
    rs={'metadata':{'uid':'rs-uid','ownerReferences':[{'controller':True,'kind':'Deployment','name':'demo','uid':'uid1'}]}}
    def execute(args,**kw):
        if 'pod' in args: return SimpleNamespace(stdout=json.dumps(pod))
        if 'replicaset' in args: return SimpleNamespace(stdout=json.dumps(rs))
        return real(args,**kw)
    ex.execute=execute
    assert s.targets(inv.id)==[{'name':'demo','uid':'uid1'}]
    assert propose(setup)['deployment']=='demo'
    pod['metadata']['uid']='recreated'
    with pytest.raises(HTTPException): s.targets(inv.id)
    assert ex.writes==0


def test_pod_target_rejects_recreated_replicaset(setup):
    s,inv,ex,_=setup
    inv.resource_type='pod'; inv.resource_name='demo-pod'
    inv.evidence={'pod':{'data':[{'name':'demo-pod','uid':'p'}]}};s.db.commit()
    def execute(args,**kw):
        data={'metadata':{'uid':'p','ownerReferences':[{'controller':True,'kind':'ReplicaSet','name':'rs','uid':'old'}]}} if 'pod' in args else {'metadata':{'uid':'new'}}
        return SimpleNamespace(stdout=json.dumps(data))
    ex.execute=execute
    with pytest.raises(HTTPException): s.targets(inv.id)


@pytest.mark.parametrize('kind,code,detail',[
    ('timeout',504,'timed out'),('connect',503,'Cannot connect'),
    ('missing',503,'HTTP 404'),('rejected',502,'HTTP 400'),
    ('truncated',502,'token limit'),('invalid',502,'required schema')])
def test_ai_generation_errors_identify_cause_without_mutation(setup,kind,code,detail):
    import httpx
    from app.ai.ollama_client import IncompleteOllamaResponse
    def generate(*args,**kw):
        assert kw['schema']['properties']['decision']['enum']==['propose','needs_information']
        assert kw['schema']['$defs']['Change']['properties']['value']['type']==['string','integer']
        if kind=='timeout': raise httpx.ReadTimeout('private payload must not leak')
        if kind=='connect': raise httpx.ConnectError('private payload must not leak')
        if kind in ('missing','rejected'):
            request=httpx.Request('POST','http://localhost:11434/api/generate')
            response=httpx.Response(404 if kind=='missing' else 400,request=request)
            raise httpx.HTTPStatusError('private payload must not leak',request=request,response=response)
        if kind=='truncated': raise IncompleteOllamaResponse('private payload must not leak')
        return '{"explanation":"private payload must not leak"}'
    setup[3].generate=generate
    with pytest.raises(HTTPException) as e: propose(setup)
    assert e.value.status_code==code and detail in e.value.detail
    assert 'private payload' not in e.value.detail and setup[2].writes==0


def test_ollama_transport_sends_schema_and_detects_truncation(monkeypatch):
    import httpx
    from app.ai.ollama_client import OllamaClient, IncompleteOllamaResponse
    sent=[]
    def post(url,**kw):
        sent.append(kw['json'])
        return httpx.Response(200,json={'done':True,'done_reason':'length','response':'{}'},request=httpx.Request('POST',url))
    monkeypatch.setattr('app.ai.ollama_client.httpx.post',post)
    schema=ModelPlan.model_json_schema()
    with pytest.raises(IncompleteOllamaResponse): OllamaClient(model='qwen3:8b').generate('data',schema=schema,num_ctx=8192,num_predict=1000)
    assert sent[0]['format']==schema and sent[0]['think'] is False
    assert sent[0]['options']['num_ctx']==8192


def test_assessment_only_constrains_model_and_has_no_apply_path(setup):
    s,inv,ex,ai=setup
    def generate(*args,**kw):
        assert kw['schema']['properties']['decision']['enum']==['needs_information']
        assert kw['schema']['properties']['changes']['maxItems']==0
        return json.dumps({**PLAN,'decision':'needs_information','changes':[]})
    ai.generate=generate
    p=s.propose(inv.id,ProposeRequest(deployment='demo',objective='Assess the exception, do not change anything.',assessment_only=True))
    assert p['state']=='ASSESSMENT' and 'diff' not in p and ex.writes==0
    with pytest.raises(HTTPException): s.validate(p['id'])
    with pytest.raises(HTTPException): s.mutate(p['id'],p['confirmation'])


def test_assessment_rejects_model_that_ignores_no_changes(setup):
    s,inv,ex,_=setup
    with pytest.raises(HTTPException) as e:
        s.propose(inv.id,ProposeRequest(deployment='demo',objective='Only assess the evidence please.',assessment_only=True))
    assert 'assessment-only' in e.value.detail and ex.writes==0


def test_schema_only_lists_paths_present_or_supported_for_live_workload(setup):
    s,inv,ex,ai=setup
    def generate(*args,**kw):
        paths=kw['schema']['$defs']['Change']['properties']['path']['enum']
        assert '/spec/template/spec/containers/0/readinessProbe/httpGet/path' in paths
        assert not any('/livenessProbe/' in p or '/initContainers/' in p or '/env/' in p for p in paths)
        return json.dumps(PLAN)
    ai.generate=generate
    propose(setup)
