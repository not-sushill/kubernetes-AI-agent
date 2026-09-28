"""Evidence-only timeline and relationships. Observations are not asserted causes."""
from datetime import datetime, timezone
import re

def section(evidence,key):
    value=evidence.get(key,{})
    return value.get('data') if isinstance(value,dict) else None

def as_list(value): return value if isinstance(value,list) else [value] if isinstance(value,dict) else []

def incident_timeline(record):
    rows=[]
    def add(at,kind,title,resource,detail=''):
        if not at:return
        try: parsed=datetime.fromisoformat(str(at).replace('Z','+00:00'));at=parsed.replace(tzinfo=timezone.utc).isoformat() if parsed.tzinfo is None else parsed.isoformat()
        except (ValueError,TypeError):return
        rows.append({'at':at,'kind':kind,'title':title,'resource':resource,'detail':str(detail)[:1500]})
    e=record.evidence or {}
    for key in ('pod','deployment','replicaset'):
        for item in as_list(section(e,key)):
            name=item.get('name','')
            add(item.get('age'),'created',key+' created',name)
            for condition in item.get('conditions',[]):
                add(condition.get('lastTransitionTime'),'condition',condition.get('type','')+'='+str(condition.get('status')),name,condition.get('message',''))
            for container in item.get('containers',[])+item.get('init_containers',[]):
                for state in ('state','last_state'):
                    terminated=(container.get(state) or {}).get('terminated') or {}
                    add(terminated.get('finishedAt'),'termination',terminated.get('reason','Container terminated'),name,container.get('name',''))
    events=section(e,'events') or {}
    events=events.get('events',[]) if isinstance(events,dict) else events
    for item in events:
        add(item.get('last_timestamp') or item.get('lastTimestamp') or item.get('event_time') or item.get('eventTime'),'event',item.get('reason','Event'),item.get('object_name') or (item.get('involvedObject') or item.get('involved_object') or {}).get('name',''),item.get('message',''))
    scanned=0
    def log_events(value,resource):
        nonlocal scanned
        if isinstance(value,dict):
            for key,child in value.items():
                if key=='logs' and isinstance(child,list):
                    for line in child:
                        if scanned>=5000:return
                        scanned+=1
                        if isinstance(line,str) and re.search(r'\b(ERROR|FATAL|WARN|WARNING|Traceback)\b',line,re.I):
                            match=re.match(r'(\d{4}-\d{2}-\d{2}T\S+)',line)
                            if match:add(match[1],'log','Log error/warning (text match)',resource,line)
                elif isinstance(child,dict):log_events(child,child.get('pod') or resource)
    log_events(section(e,'logs'),record.resource_name)
    add(record.created_at.isoformat(),'investigation',record.status,record.resource_name)
    rows.sort(key=lambda r:datetime.fromisoformat(r['at']))
    return {'items':rows[-500:],'limited':len(rows)>500,'source':'Saved investigation evidence; event retention and collection limits apply.'}

def relationships(items):
    nodes=[];edges=[];by_uid={}
    for item in items:
        m=item.get('metadata',{});uid=m.get('uid')
        if not uid:continue
        by_uid[uid]=item
        status=item.get('status',{})
        nodes.append({'id':uid,'kind':item.get('kind'),'name':m.get('name'),'namespace':m.get('namespace',''),'status':(str(status.get('phase','Unknown'))+' · '+('Ready' if any(c.get('type')=='Ready' and c.get('status')=='True' for c in status.get('conditions',[])) else 'Readiness unconfirmed')) if item.get('kind')=='Pod' else str(status.get('readyReplicas',0))+'/'+str(item.get('spec',{}).get('replicas',1))+' ready' if item.get('kind') in ('Deployment','ReplicaSet') else ''})
    for uid,item in by_uid.items():
        m=item['metadata'];kind=item.get('kind');spec=item.get('spec',{})
        for owner in m.get('ownerReferences',[]):
            if owner.get('uid') in by_uid:edges.append({'from':owner['uid'],'to':uid,'relation':'owns'})
        if kind=='Service' and spec.get('selector'):
            for target,pod in by_uid.items():
                if pod.get('kind')=='Pod' and pod['metadata'].get('namespace')==m.get('namespace') and all(pod['metadata'].get('labels',{}).get(k)==v for k,v in spec['selector'].items()):edges.append({'from':uid,'to':target,'relation':'selects'})
        if kind=='Pod' and spec.get('nodeName'):
            node='node:'+spec['nodeName']
            if not any(n['id']==node for n in nodes):nodes.append({'id':node,'kind':'Node','name':spec['nodeName'],'namespace':'','status':'Not collected'})
            edges.append({'from':uid,'to':node,'relation':'scheduled on'})
        if kind=='Ingress':
            backends=[spec.get('defaultBackend',{})]+[p.get('backend',{}) for r in spec.get('rules',[]) for p in r.get('http',{}).get('paths',[])]
            for backend in backends:
                name=backend.get('service',{}).get('name')
                for target,service in by_uid.items():
                    if service.get('kind')=='Service' and service['metadata'].get('name')==name and service['metadata'].get('namespace')==m.get('namespace'):edges.append({'from':uid,'to':target,'relation':'routes to'})
    unique={tuple(edge.values()):edge for edge in edges}
    return {'nodes':nodes,'edges':list(unique.values())}
