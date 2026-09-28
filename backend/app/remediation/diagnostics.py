"""Fixed read-only checks. Model text is never interpreted as a command."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import time

from app.remediation.models import DiagnosticRun
from app.remediation.service import editable, fail, now

CHECKS = {
    'deployment_status': ('Deployment rollout and images', 'Read replica availability, conditions, image references and probe settings.'),
    'pod_status': ('Owned pod health', 'Read phase, readiness, restart counts and waiting/termination reasons for owned pods.'),
    'warning_events': ('Recent retained warning events', 'Read warning events for the Deployment and its owned pods; event retention is limited.'),
}

def fingerprint(spec):
    return hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class DiagnosticService:
    def __init__(self, fixes):
        self.fixes = fixes
        self.db = fixes.db

    def catalog(self, ident):
        p=self.fixes.load(ident).payload
        prefix=['kubectl','--context',p['context'],'-n',p['namespace'],'--request-timeout=15s']
        common=prefix+['get','deployment',p['deployment'],'-o','json']
        inventory=[prefix+['get','replicasets','-o','json'],prefix+['get','pods','-o','json']]
        return [{'id':key,'title':title,'purpose':purpose,'read_only':True,
            'commands':[common]+(inventory if key!='deployment_status' else [])+
            ([prefix+['get','events','--field-selector','type=Warning','-o','json']] if key=='warning_events' else [])+([common] if key!='deployment_status' else [])}
            for key,(title,purpose) in CHECKS.items()]

    def list(self, ident):
        self.fixes.load(ident)
        return [{'id':r.id,**r.payload} for r in self.db.query(DiagnosticRun).filter_by(proposal_id=ident).order_by(DiagnosticRun.created_at.desc()).limit(20).all()]

    def run(self, ident, check_id):
        if check_id not in CHECKS: fail('Unsupported diagnostic check.',422)
        p=deepcopy(self.fixes.load(ident).payload)
        commands=next(c['commands'] for c in self.catalog(ident) if c['id']==check_id)
        run=DiagnosticRun(proposal_id=ident,payload={'check_id':check_id,'title':CHECKS[check_id][0],
            'state':'RUNNING','started_at':now(),'context':p['context'],'namespace':p['namespace'],
            'deployment':p['deployment'],'commands':commands,'executed_commands':[]})
        self.db.add(run);self.db.commit();self.db.refresh(run)
        result=deepcopy(run.payload)
        deadline=time.monotonic()+60
        def execute(command):
            remaining=int(deadline-time.monotonic())
            if remaining<1: raise TimeoutError('Diagnostic deadline exceeded.')
            result['executed_commands'].append(command)
            return json.loads(self.fixes.executor.execute(command[1:],timeout=min(20,remaining)).stdout)
        try:
            live=execute(commands[0])
            if live['metadata']['uid']!=p['uid']: fail('Deployment was replaced. Run a fresh investigation.')
            result.update(uid=p['uid'],spec_hash=fingerprint(live['spec']))
            output={'captured_at':now()}
            if check_id=='deployment_status':
                output.update(generation=live['metadata'].get('generation'),status=live.get('status',{}),configuration=editable(live['spec']))
            else:
                rs=execute(commands[1]).get('items',[])
                rs_ids={r['metadata']['uid'] for r in rs if any(o.get('controller') and o.get('kind')=='Deployment' and o.get('uid')==p['uid'] for o in r['metadata'].get('ownerReferences',[]))}
                pods=[pod for pod in execute(commands[2]).get('items',[]) if any(o.get('controller') and o.get('kind')=='ReplicaSet' and o.get('uid') in rs_ids for o in pod['metadata'].get('ownerReferences',[]))]
                output['owned_pod_count']=len(pods)
                if check_id=='pod_status':
                    output['pods']=[{'name':pod['metadata']['name'],'uid':pod['metadata']['uid'],'phase':pod.get('status',{}).get('phase'),
                        'conditions':pod.get('status',{}).get('conditions',[]),
                        'containers':[{k:c.get(k) for k in ('name','ready','restartCount','state','lastState','image')} for c in (pod.get('status',{}).get('initContainerStatuses',[])+pod.get('status',{}).get('containerStatuses',[]))[:20]]} for pod in pods[:20]]
                    output['pod_sample_limited']=len(pods)>20
                else:
                    ids={p['uid']} | {pod['metadata']['uid'] for pod in pods} | rs_ids
                    events=[e for e in execute(commands[3]).get('items',[]) if e.get('involvedObject',{}).get('uid') in ids]
                    events.sort(key=lambda e:e.get('lastTimestamp') or e.get('eventTime') or e.get('metadata',{}).get('creationTimestamp',''),reverse=True)
                    output['events']=[{k:e.get(k) for k in ('reason','message','count','firstTimestamp','lastTimestamp','eventTime','involvedObject')} for e in events[:30]]
                    output['event_sample_limited']=len(events)>30
            if check_id!='deployment_status':
                verified=execute(commands[-1])
                if verified['metadata']['uid']!=p['uid'] or fingerprint(verified['spec'])!=result['spec_hash']:
                    fail('Deployment changed during diagnostic collection; run the check again.')
            text=json.dumps(output,ensure_ascii=False,default=str)
            result.update(state='COMPLETED',output=text[:12000],truncated=len(text)>12000)
        except Exception as exc:
            # No raw exception repr: command errors can include unwanted payloads.
            detail=getattr(exc,'detail',None) or getattr(exc,'stderr',None) or str(exc)
            result.update(state='FAILED',output=str(detail)[:1500],truncated=False)
        result['finished_at']=now()
        run.payload=result;self.db.commit();self.db.refresh(run)
        return {'id':run.id,**run.payload}

    def evidence(self, source_id, investigation_id, target, live):
        source=self.fixes.load(source_id)
        if source.investigation_id!=investigation_id or any(source.payload[k]!=target[k] for k in ('context','namespace','deployment')):
            fail('Diagnostic source belongs to another investigation or target.',422)
        rows=self.list(source_id)
        accepted=[]
        for r in rows:
            if r['state']!='COMPLETED' or r.get('uid')!=live['metadata']['uid'] or r.get('spec_hash')!=fingerprint(live['spec']): continue
            if (datetime.now(timezone.utc)-datetime.fromisoformat(r['finished_at'])).total_seconds()>900: continue
            if any(item['check_id']==r['check_id'] for item in accepted): continue
            accepted.append(r)
        return accepted[:3]
