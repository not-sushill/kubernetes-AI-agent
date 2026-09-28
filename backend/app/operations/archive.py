"""Read existing Loki archives with exact selectors and bounded requests."""
import json
from app.operations.config import config
import re
from datetime import datetime, timedelta
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

class ArchiveQuery(BaseModel):
    cluster: str = Field(min_length=1,max_length=253)
    namespace: str = Field(min_length=1,max_length=253)
    pod: str = Field(default='',max_length=253)
    container: str = Field(default='',max_length=253)
    text: str = Field(default='',max_length=300)
    start: datetime
    end: datetime
    limit: int = Field(default=1000,ge=1,le=5000)
    @model_validator(mode='after')
    def dates(self):
        if not self.start.tzinfo or not self.end.tzinfo: raise ValueError('Use timestamps with timezone offsets.')
        if not timedelta(0)<self.end-self.start<=timedelta(days=7): raise ValueError('Choose a positive range of at most seven days.')
        return self

def logql(q):
    selectors=[]
    for field in ('cluster','namespace','pod','container'):
        label=config('LOKI_LABEL_'+field.upper(),field)
        if not re.fullmatch('[a-zA-Z_][a-zA-Z0-9_]*',label): raise HTTPException(503,'Invalid archive label configuration.')
        value=getattr(q,field)
        if value: selectors.append(label+'='+json.dumps(value))
    return '{'+','.join(selectors)+'}'+(' |= '+json.dumps(q.text) if q.text else '')

def query_archive(q):
    url=config('LOKI_URL','').rstrip('/')
    if not url: raise HTTPException(503,'Configure LOKI_URL and a log collector first. Earlier logs cannot be recovered retroactively.')
    headers={}
    if config('LOKI_TOKEN'): headers['Authorization']='Bearer '+config('LOKI_TOKEN')
    if config('LOKI_TENANT'): headers['X-Scope-OrgID']=config('LOKI_TENANT')
    params={'query':logql(q),'start':str(int(q.start.timestamp()*1_000_000_000)),'end':str(int(q.end.timestamp()*1_000_000_000)),'limit':q.limit,'direction':'forward'}
    try:
        with httpx.Client(timeout=25,follow_redirects=False) as client:
            with client.stream('GET',url+'/loki/api/v1/query_range',params=params,headers=headers) as response:
                response.raise_for_status();body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>8_000_000: raise HTTPException(413,'Archive response too large. Narrow the time range.')
        result=json.loads(body)
        if result.get('status')!='success' or result.get('data',{}).get('resultType')!='streams': raise ValueError()
        rows=[{'timestamp':v[0],'line':v[1],'labels':stream.get('stream',{})} for stream in result['data']['result'] for v in stream.get('values',[])]
        rows.sort(key=lambda row:int(row['timestamp']))
        return {'cluster':q.cluster,'namespace':q.namespace,'pod':q.pod,'rows':rows[:q.limit],'limit_reached':len(rows)>=q.limit,'source':'Loki','start':q.start,'end':q.end}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,'Archive query failed. Check Loki connectivity, credentials and label mapping.') from exc
