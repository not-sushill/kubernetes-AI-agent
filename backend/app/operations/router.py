from copy import deepcopy
import difflib
import json
from app.operations.config import config
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from sqlalchemy import update
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from app.db.database import get_db
from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.context_manager import KubernetesContextManager
from app.kubernetes.validators import validate_namespace
from app.investigations.models import InvestigationCreate
from app.models.investigation import Investigation
from app.operations.models import OperationRecord
from app.operations.archive import ArchiveQuery, query_archive
from app.operations.jobs import create_job, timestamp
from app.operations.evidence import incident_timeline, relationships
from app.operations.verification import verify
from app.remediation.models import FixProposal
from app.remediation.service import FixService, editable
from app.remediation.diagnostics import DiagnosticService, CHECKS

router=APIRouter(prefix='/v1/operations',tags=['Operations'])

def view(row):return {'id':row.id,'state':row.state,'created_at':row.created_at,**row.payload}
def load(db,ident,kind):
    row=db.get(OperationRecord,ident)
    if not row or row.kind!=kind:raise HTTPException(404,'Record not found.')
    return row

def known_context(context):
    contexts=KubectlExecutor().execute(['config','get-contexts','-o','name'],timeout=10).stdout.splitlines()
    if context not in contexts:raise HTTPException(422,'Unknown Kubernetes context.')

class JobRequest(InvestigationCreate):
    context: str=Field(min_length=1,max_length=500)

@router.get('/capabilities')
def capabilities(request:Request):
    return {'archive_configured':bool(config('LOKI_URL')),'notifications_configured':bool(config('ALERT_WEBHOOK_URL')),'team_access':config('TEAM_USERS_JSON','[]').strip() not in ('','[]'),'actor':getattr(request.state,'actor','local'),'role':getattr(request.state,'role','admin')}

@router.post('/jobs',status_code=202)
def enqueue(body:JobRequest,request:Request,db=Depends(get_db)):
    known_context(body.context)
    return view(create_job(db,InvestigationCreate.model_validate(body.model_dump()),body.context,getattr(request.state,'actor','local')))

@router.get('/jobs')
def jobs(db=Depends(get_db)):
    return [view(r) for r in db.query(OperationRecord).filter_by(kind='job').order_by(OperationRecord.created_at.desc()).limit(100)]

@router.get('/jobs/{ident}')
def job(ident:str,db=Depends(get_db)):return view(load(db,ident,'job'))

@router.post('/archive')
def archive(body:ArchiveQuery):return query_archive(body)

@router.get('/timeline/{ident}')
def timeline(ident:str,db=Depends(get_db)):
    row=db.get(Investigation,ident)
    if not row:raise HTTPException(404,'Investigation not found.')
    result=incident_timeline(row)
    for fix in db.query(FixProposal).filter_by(investigation_id=ident).all():
        for e in fix.payload.get('audit',[]):
            result['items'].append({'at':e.get('time'),'kind':'change','title':e.get('event','Change recorded'),'resource':fix.payload.get('deployment'),'detail':fix.state})
    result['items'].sort(key=lambda x:x['at'] or '')
    return result

@router.get('/relationships')
def graph(context:str=Query(min_length=1,max_length=500),namespace:str=Query(min_length=1,max_length=253)):
    validate_namespace(namespace);known_context(context)
    args=['--context',context,'-n',namespace,'--request-timeout=15s','get','pods,replicasets,deployments,services,ingresses','-o','json']
    try:
        result=json.loads(KubectlExecutor().execute(args,timeout=20).stdout)
        items=result.get('items',[])
        if len(items)>1500:raise HTTPException(413,'Namespace too large for this view (1500 objects maximum).')
        return {**relationships(items),'context':context,'namespace':namespace,'captured_at':timestamp()}
    except HTTPException:raise
    except Exception as exc:raise HTTPException(502,'Could not collect relationships. Check Kubernetes access.') from exc

@router.get('/changes/{ident}')
def changes(ident:str,db=Depends(get_db)):
    rows=db.query(FixProposal).filter_by(investigation_id=ident).order_by(FixProposal.created_at.desc()).limit(50).all()
    result=[]
    for row in rows:
        p=row.payload
        before=json.dumps(editable(p['before']),indent=2,sort_keys=True).splitlines() if p.get('before') else []
        after=json.dumps(editable(p['after']),indent=2,sort_keys=True).splitlines() if p.get('after') else before
        result.append({'id':row.id,'state':row.state,'deployment':p.get('deployment'),'context':p.get('context'),'history':p.get('audit',[]),'diff':'\n'.join(difflib.unified_diff(before,after,fromfile='before',tofile='proposed',lineterm=''))})
    return result

@router.post('/fixes/{ident}/verify')
def verification(ident:str,db=Depends(get_db)):return verify(db,ident)

@router.get('/fixes/{ident}/verifications')
def verifications(ident:str,db=Depends(get_db)):
    return [view(r) for r in db.query(OperationRecord).filter_by(kind='verification').order_by(OperationRecord.created_at.desc()).limit(200).all() if r.payload.get('proposal_id')==ident][:20]

BUILTINS=[{'id':'image-pull','name':'Image pull failure','checks':['deployment_status','pod_status','warning_events']}, {'id':'readiness','name':'Readiness / rollout','checks':['deployment_status','pod_status','warning_events']}, {'id':'oom','name':'Memory termination','checks':['pod_status','warning_events']}, {'id':'database','name':'Database connectivity triage','checks':['pod_status','warning_events']}]
class RunbookBody(BaseModel):
    name:str=Field(min_length=3,max_length=80)
    checks:list[str]=Field(min_length=1,max_length=3)
    @field_validator('checks')
    @classmethod
    def allowed(cls,values):
        if any(v not in CHECKS for v in values) or len(set(values))!=len(values):raise ValueError('Use unique approved check IDs.')
        return values
class RunbookRun(BaseModel):
    proposal_id:str=Field(min_length=1,max_length=100)

@router.get('/runbooks')
def runbooks(db=Depends(get_db)):return BUILTINS+[view(r) for r in db.query(OperationRecord).filter_by(kind='runbook').order_by(OperationRecord.created_at.desc()).limit(100)]

@router.post('/runbooks')
def save_runbook(body:RunbookBody,db=Depends(get_db)):
    row=OperationRecord(kind='runbook',payload=body.model_dump());db.add(row);db.commit();db.refresh(row);return view(row)

@router.post('/runbooks/{ident}/run')
def run_book(ident:str,body:RunbookRun,db=Depends(get_db)):
    book=next((b for b in BUILTINS if b['id']==ident),None)
    if book is None:book=load(db,ident,'runbook').payload
    diagnostics=DiagnosticService(FixService(db))
    return {'runs':[diagnostics.run(body.proposal_id,c) for c in book['checks']]}

@router.get('/alerts')
def alerts(db=Depends(get_db)):
    rows=db.query(OperationRecord).filter_by(kind='alert').order_by(OperationRecord.created_at.desc()).limit(100).all()
    counts={}
    for row in rows:counts[row.payload['key']]=counts.get(row.payload['key'],0)+1
    return [{**view(r),'occurrences_in_recent_100':counts[r.payload['key']]} for r in rows]

@router.post('/alerts/{ident}/acknowledge')
def acknowledge(ident:str,request:Request,db=Depends(get_db)):
    row=load(db,ident,'alert');p=dict(row.payload);p.update(acknowledged_at=timestamp(),acknowledged_by=getattr(request.state,'actor','local'));row.payload=p;db.commit();return view(row)

@router.post('/alerts/{ident}/notify')
def notify(ident:str,db=Depends(get_db)):
    row=load(db,ident,'alert');url=config('ALERT_WEBHOOK_URL','')
    if not url:raise HTTPException(503,'Configure ALERT_WEBHOOK_URL first.')
    if urlparse(url).scheme!='https':raise HTTPException(503,'Notification destination must use HTTPS.')
    if row.payload.get('notified_at'):raise HTTPException(409,'This alert was already delivered.')
    if row.state in ('NOTIFYING','DELIVERY_UNKNOWN','DELIVERED'):raise HTTPException(409,'Delivery already attempted; inspect the receiver before retrying.')
    claimed=db.execute(update(OperationRecord).where(OperationRecord.id==ident,OperationRecord.state=='OPEN').values(state='NOTIFYING'));db.commit()
    if claimed.rowcount!=1:raise HTTPException(409,'Another notification is already in progress.')
    # Only metadata is delivered; no raw logs, tokens, YAML or evidence.
    payload={k:row.payload[k] for k in ('title','severity','namespace','resource','investigation_id')}
    payload['url']=config('CONSOLE_URL','http://localhost:3000').rstrip('/')+'/investigations/'+payload['investigation_id']
    try:
        with httpx.Client(timeout=10,follow_redirects=False) as client:client.post(url,json=payload).raise_for_status()
    except Exception as exc:
        row.state='DELIVERY_UNKNOWN';db.commit()
        raise HTTPException(502,'Notification delivery failed or is unconfirmed; inspect the receiver before retrying.') from exc
    p=dict(row.payload);p['notified_at']=timestamp();row.payload=p;row.state='DELIVERED';db.commit();return view(row)

@router.get('/audit')
def audit_records(db=Depends(get_db)):
    return [view(r) for r in db.query(OperationRecord).filter_by(kind='audit').order_by(OperationRecord.created_at.desc()).limit(200)]
