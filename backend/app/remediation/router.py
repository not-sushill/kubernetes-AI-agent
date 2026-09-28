from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.db.database import get_db
from app.kubernetes.exceptions import KubernetesError
from app.remediation.models import ProposeRequest, Approval
from app.remediation.service import FixService
import yaml


def local_origin(request: Request):
    if request.method != 'GET' and request.headers.get('origin') not in (None,'http://localhost:3000','http://127.0.0.1:3000'):
        raise HTTPException(403,'Fix operations are restricted to the local UI.')

router = APIRouter(prefix='/v1',tags=['AI fix assistance'],dependencies=[Depends(local_origin)])

def service(db=Depends(get_db)):
    return FixService(db)


def invoke(call):
    try: return call()
    except KubernetesError as exc:
        raise HTTPException(502,'Kubernetes operation failed. ' + str(getattr(exc,'stderr',str(exc)))[:1500]) from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc

@router.get('/investigations/{investigation_id}/fixes')
def list_fixes(investigation_id: str, s=Depends(service)):
    return s.list(investigation_id)

@router.post('/investigations/{investigation_id}/fixes')
def propose(investigation_id: str, request: ProposeRequest, s=Depends(service)):
    return invoke(lambda: s.propose(investigation_id,request))

@router.post('/fixes/{ident}/validate')
def validate(ident: str, s=Depends(service)):
    return invoke(lambda: s.validate(ident))

@router.post('/fixes/{ident}/apply')
def apply(ident: str, request: Approval, s=Depends(service)):
    return invoke(lambda: s.mutate(ident,request.confirmation))

@router.post('/fixes/{ident}/rollback')
def rollback(ident: str, request: Approval, s=Depends(service)):
    return invoke(lambda: s.mutate(ident,request.confirmation,rollback=True))

@router.get('/fixes/{ident}/backup',response_class=PlainTextResponse)
def backup(ident: str, s=Depends(service)):
    p = s.load(ident).payload
    return yaml.safe_dump({'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':p['deployment'],'namespace':p['namespace']},'spec':p['before']},sort_keys=False)

@router.get('/investigations/{investigation_id}/fix-targets')
def targets(investigation_id: str, s=Depends(service)):
    return invoke(lambda: s.targets(investigation_id))

from app.remediation.diagnostics import DiagnosticService
from app.remediation.models import RunCheck

@router.get('/fixes/{ident}/diagnostic-checks')
def diagnostic_checks(ident: str, s=Depends(service)):
    return DiagnosticService(s).catalog(ident)

@router.get('/fixes/{ident}/diagnostic-runs')
def diagnostic_runs(ident: str, s=Depends(service)):
    return DiagnosticService(s).list(ident)

@router.post('/fixes/{ident}/diagnostic-runs')
def run_diagnostic(ident: str, request: RunCheck, s=Depends(service)):
    return invoke(lambda: DiagnosticService(s).run(ident,request.check_id))
