from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from tests.test_ai_fixes import setup, propose, BASE, PLAN
from app.remediation.diagnostics import DiagnosticService, fingerprint
from app.remediation.models import ProposeRequest, DiagnosticRun
from app.kubernetes.services.investigation.correlation.pod_root_cause import PodRootCauseService


def executor(ex):
    original=ex.execute
    def execute(args,**kw):
        assert args[:4]==['--context','cluster-a','-n','default']
        if 'replicasets' in args:
            data={'items':[{'metadata':{'uid':'rs','ownerReferences':[{'kind':'Deployment','controller':True,'uid':'uid1'}]}}]}
        elif 'pods' in args:
            data={'items':[{'metadata':{'name':'owned','uid':'pod','ownerReferences':[{'kind':'ReplicaSet','controller':True,'uid':'rs'}]},'status':{'phase':'Running','containerStatuses':[{'name':'web','ready':True,'restartCount':0}]}},{'metadata':{'name':'unrelated','uid':'other'},'spec':{'secrets':'never return'}}]}
        elif 'events' in args:
            data={'items':[{'involvedObject':{'uid':'pod'},'reason':'Unhealthy','message':'probe failure'},{'involvedObject':{'uid':'other'},'message':'unrelated'}]}
        else: return original(args,**kw)
        ex.calls.append(args);return SimpleNamespace(stdout=json.dumps(data))
    ex.execute=execute

@pytest.mark.parametrize('check',['deployment_status','pod_status','warning_events'])
def test_fixed_checks_read_only_scoped_and_saved(setup,check):
    p=propose(setup);s,_,ex,_=setup;executor(ex)
    d=DiagnosticService(s);run=d.run(p['id'],check)
    assert run['state']=='COMPLETED' and ex.writes==0
    assert 'secret-value' not in run['output'] and 'secret-header' not in run['output'] and 'unrelated' not in run['output']
    assert d.list(p['id'])[0]['id']==run['id']
    assert all('get' in c and not any(x in c for x in ('apply','patch','exec','delete')) for c in run['executed_commands'])


def test_unknown_command_and_recreated_deployment_blocked(setup):
    p=propose(setup);s,_,ex,_=setup;d=DiagnosticService(s)
    with pytest.raises(HTTPException): d.run(p['id'],'kubectl delete pods')
    ex.obj['metadata']['uid']='recreated'
    assert d.run(p['id'],'deployment_status')['state']=='FAILED' and ex.writes==0


def test_fresh_checks_feed_new_assessment_without_mutation(setup):
    p=propose(setup);s,inv,ex,ai=setup
    DiagnosticService(s).run(p['id'],'deployment_status')
    def generate(prompt,**kw):
        assert 'Live check:' in prompt and 'secret-value' not in prompt
        return json.dumps({**PLAN,'decision':'needs_information','changes':[],'hypotheses':[{'explanation':'The current status needs correlation with the incident.','evidence_ids':[1],'confidence':'low','uncertainty':'No application behavior check has been performed.','check_id':'manual_check'}]})
    ai.generate=generate
    out=s.propose(inv.id,ProposeRequest(deployment='demo',objective='Assess current health using the new check.',assessment_only=True,source_proposal_id=p['id']))
    assert out['state']=='ASSESSMENT' and out['id']!=p['id'] and out['diagnostic_run_ids']
    assert out['hypotheses'][0]['evidence_ids']==[1] and ex.writes==0

@pytest.mark.parametrize('stale',['spec','age'])
def test_stale_diagnostic_evidence_is_rejected(setup,stale):
    p=propose(setup);s,inv,ex,_=setup;run=DiagnosticService(s).run(p['id'],'deployment_status')
    if stale=='spec': ex.obj['spec']['replicas']=3
    else:
        row=s.db.get(DiagnosticRun,run['id']);row.payload={**row.payload,'finished_at':'2020-01-01T00:00:00+00:00'};s.db.commit()
    with pytest.raises(HTTPException): s.propose(inv.id,ProposeRequest(deployment='demo',objective='Assess again please with live evidence.',assessment_only=True,source_proposal_id=p['id']))

@pytest.mark.parametrize('message,title',[
 ('java.lang.IllegalArgumentException: Invalid character found in the request target [/?error=[authorization_request_not_found] ]','Invalid HTTP request target rejected'),
 ("mysql.connector.errors.ProgrammingError: 1142 (42000): SELECT command denied to user admin for table mst_patient",'Database SELECT permission denied')])
def test_precise_log_classification_does_not_invent_rbac_or_outage(message,title):
    result=PodRootCauseService().analyze({}, {'issues':[{'category':'logs','severity':'warning','title':'Application exception detected','evidence':[message]}]})
    causes=result['root_causes']
    assert any(c['title']==title for c in causes)
    assert not any(c['title'] in ('Application runtime failure','Permission or authorization failure') for c in causes)
