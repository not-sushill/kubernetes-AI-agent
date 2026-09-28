"""Optional per-user API tokens. No request bodies, token values or log text in audit."""
import hashlib
import hmac
import json
from app.operations.config import config
import re
from datetime import datetime, timezone
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.database import SessionLocal
from app.operations.models import OperationRecord

ROLES = {'viewer': 0, 'operator': 1, 'approver': 2, 'admin': 3}

def configured_users():
    users = json.loads(config('TEAM_USERS_JSON', '[]'))
    if not isinstance(users, list): raise ValueError('TEAM_USERS_JSON must be a list')
    names=set(); hashes=set()
    for u in users:
        if u.get('role') not in ROLES or not re.fullmatch(r'[a-fA-F0-9]{64}',u.get('token_sha256','')) or not u.get('name') or u['name'] in names or u['token_sha256'].lower() in hashes:
            raise ValueError('Invalid team user configuration')
        names.add(u['name']);hashes.add(u['token_sha256'].lower())
    return users

def required_role(method, path):
    if path.endswith('/audit'): return 3
    if method in ('GET','HEAD','OPTIONS'): return 0
    # Every mutation is approver-only unless specifically read-only or workflow metadata.
    if path.endswith(('/apply','/restore','/rollback','/upload','/terminal')): return 2
    if path.endswith('/contexts/select'): return 3
    if path.endswith(('/jobs','/archive','/runbooks','/diagnostic-runs','/verify','/validate','/notify','/acknowledge')): return 1
    if '/runbooks/' in path and path.endswith('/run'): return 1
    if path.endswith('/download'): return 1
    if re.search(r'/v1/investigations(?:/[^/]+/fixes)?$',path): return 1
    return 2

def audit(actor, method, path, status):
    with SessionLocal() as db:
        db.add(OperationRecord(kind='audit',state='RECORDED',payload={'actor':actor,'method':method,'path':path[:500], 'status':status,'at':datetime.now(timezone.utc).isoformat()}));db.commit()

class TeamAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        users=configured_users()
        actor='local'; role='admin'; status=None
        path=request.url.path
        if request.method=='OPTIONS' or path in ('/api/health','/'):
            return await call_next(request)
        if users:
            supplied=request.headers.get('x-api-key','')
            digest=hashlib.sha256(supplied.encode()).hexdigest()
            user=next((u for u in users if supplied and hmac.compare_digest(digest,u['token_sha256'].lower())),None)
            if not user: return JSONResponse({'detail':'API token required.'},status_code=401)
            actor=user['name'];role=user['role']
            if ROLES[role]<required_role(request.method,path):
                audit(actor,request.method,path,403)
                return JSONResponse({'detail':'Your role cannot perform this operation.'},status_code=403)
        request.state.actor=actor;request.state.role=role
        try:
            response=await call_next(request);status=response.status_code;return response
        finally:
            if request.method not in ('GET','HEAD','OPTIONS'):
                audit(actor,request.method,path,status or 500)
