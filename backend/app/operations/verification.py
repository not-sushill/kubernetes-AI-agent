"""Post-change checks are read-only snapshots, never automatic rollback."""
import json
import re
import time
from copy import deepcopy
from fastapi import HTTPException
from app.operations.models import OperationRecord
from app.operations.jobs import timestamp
from app.remediation.service import FixService
from app.remediation.diagnostics import fingerprint

ERROR = re.compile(r'\b(?:ERROR|FATAL|Traceback|panic:)\b',re.I)

def verify(db,ident,executor=None):
    fixes=FixService(db,executor=executor)
    row=fixes.load(ident);p=deepcopy(row.payload)
    if row.state not in ('APPLIED','APPLIED_UNCONFIRMED','ROLLED_BACK','ROLLED_BACK_UNCONFIRMED'):
        raise HTTPException(409,'Verification requires an applied change or rollback.')
    expected=p['before'] if row.state.startswith('ROLLED_BACK') else p['after']
    deadline=time.monotonic()+75
    def execute(args):
        remaining=int(deadline-time.monotonic())
        if remaining<1:raise TimeoutError('Verification deadline exceeded')
        return fixes.executor.execute(args,timeout=min(15,remaining))
    prefix=['--context',p['context'],'-n',p['namespace'],'--request-timeout=10s']
    def get(kind,name=None):
        return json.loads(execute(prefix+['get',kind]+([name] if name else [])+['-o','json']).stdout)
    result={'proposal_id':ident,'context':p['context'],'namespace':p['namespace'],'deployment':p['deployment'],'at':timestamp(),'checks':[],'limitations':[]}
    checks=result['checks']
    def check(name,passed,detail):checks.append({'name':name,'passed':passed,'detail':detail})
    try:
        live=get('deployment',p['deployment'])
        same=live['metadata']['uid']==p['uid'] and fingerprint(live['spec'])==fingerprint(expected)
        check('Approved configuration still present',same,'UID and full spec compared.')
        if not same:raise ValueError('Deployment changed since approval.')
        desired=live['spec'].get('replicas',1);status=live.get('status',{})
        check('Rollout',status.get('observedGeneration',0)>=live['metadata'].get('generation',0) and status.get('updatedReplicas',0)==desired and status.get('availableReplicas',0)==desired and status.get('replicas',0)==desired,f'{status.get("availableReplicas",0)}/{desired} available')
        rsids={r['metadata']['uid'] for r in get('replicasets').get('items',[]) if any(o.get('uid')==p['uid'] and o.get('controller') for o in r['metadata'].get('ownerReferences',[]))}
        pods=[pod for pod in get('pods').get('items',[]) if not pod['metadata'].get('deletionTimestamp') and any(o.get('uid') in rsids and o.get('controller') for o in pod['metadata'].get('ownerReferences',[]))]
        healthy=[pod for pod in pods if any(c.get('type')=='Ready' and c.get('status')=='True' for c in pod.get('status',{}).get('conditions',[]))]
        check('Owned pods ready',len(healthy)==len(pods) and len(healthy)>=desired,f'{len(healthy)}/{len(pods)} ready')
        services=[s for s in get('services').get('items',[]) if s.get('spec',{}).get('selector') and any(all(pod['metadata'].get('labels',{}).get(k)==v for k,v in s['spec']['selector'].items()) for pod in pods)]
        slices=get('endpointslices').get('items',[])
        owned={pod['metadata']['uid'] for pod in pods}
        for service in services:
            name=service['metadata']['name']
            endpoints=[e for sl in slices if sl['metadata'].get('labels',{}).get('kubernetes.io/service-name')==name for e in sl.get('endpoints',[]) if e.get('targetRef',{}).get('uid') in owned and e.get('conditions',{}).get('ready') is True and not e.get('conditions',{}).get('terminating')]
            check('Service '+name,bool(endpoints),'Ready endpoints targeting owned pods: '+str(len(endpoints)))
        if not services:result['limitations'].append('No Service matched owned pods; endpoint routing was not verified.')
        events=p.get('audit',[])
        since=next((e.get('time') for e in reversed(events) if e.get('time')),None)
        # Read only recent logs. A bounded sample cannot establish complete absence of errors.
        for pod in pods[:5]:
            for container in pod.get('spec',{}).get('containers',[])[:2]:
                args=prefix+['logs',pod['metadata']['name'],'-c',container['name'],'--tail=200','--timestamps=true']
                args+=['--since-time='+since] if since else ['--since=10m']
                try:
                    logs=execute(args).stdout
                    count=sum(bool(ERROR.search(line)) for line in logs.splitlines())
                    check('Recent logs: '+pod['metadata']['name']+'/'+container['name'],None if not logs else count==0,f'{count} error-keyword lines in a sample of {len(logs.splitlines())} lines')
                except Exception:check('Recent logs: '+pod['metadata']['name'],None,'Unavailable')
        result['limitations'].append('Logs are sampled (5 pods, 2 containers, 200 lines each). Health checks do not prove the original application issue is resolved.')
        final=get('deployment',p['deployment'])
        check('Configuration stable during checks',final['metadata']['uid']==p['uid'] and fingerprint(final['spec'])==fingerprint(expected),'Rechecked after collection.')
        result['state']='CHECKS_PASSED' if all(c['passed'] is True for c in checks) and desired>0 else 'NEEDS_REVIEW'
    except Exception:
        result['state']='INCOMPLETE';result['limitations'].append('Collection failed or Deployment changed. Recheck the target before acting.')
    saved=OperationRecord(kind='verification',state=result['state'],payload=result);db.add(saved);db.commit();db.refresh(saved)
    return {'id':saved.id,**result}
