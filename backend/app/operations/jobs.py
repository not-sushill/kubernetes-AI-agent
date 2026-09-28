"""Durable single-worker local queue; interrupted work is visible, never silently repeated."""
from copy import deepcopy
from datetime import datetime, timezone
from threading import Event, Thread, Lock
from types import SimpleNamespace
from sqlalchemy import update
from app.db.database import SessionLocal
from app.operations.models import OperationRecord
from app.operations.config import config
from app.operations.locking import WorkerFileLock
from app.investigations.models import InvestigationCreate
from app.investigations.service import InvestigationService
from app.kubernetes.executor import bound_context

stop = Event()
worker = None
worker_lock = None
lifecycle_lock = Lock()

def timestamp(): return datetime.now(timezone.utc).isoformat()

def create_job(db, request, context, actor):
    if db.query(OperationRecord).filter(OperationRecord.kind=='job',OperationRecord.state.in_(['QUEUED','RUNNING'])).count()>=100:
        from fastapi import HTTPException
        raise HTTPException(429,'Investigation queue is full.')
    row=OperationRecord(kind='job',state='QUEUED',payload={'request':request.model_dump(mode='json'),'context':context,'actor':actor,'stage':'Queued','queued_at':timestamp()})
    db.add(row);db.commit();db.refresh(row);return row

def update_job(db,row,**values):
    p=deepcopy(row.payload);p.update(values);row.payload=p;db.commit()

def record_alerts(db, investigation, context="unknown"):
    findings=investigation.analysis.root_causes
    for f in findings:
        if str(f.get('severity','')).lower() not in ('critical','high'): continue
        key='|'.join([context,investigation.target.namespace,investigation.target.resource_name,f.get('title','')])
        db.add(OperationRecord(kind='alert',state='OPEN',payload={'investigation_id':investigation.id,'context':context,'key':key,'title':f.get('title','Finding'),'severity':f.get('severity'),'namespace':investigation.target.namespace,'resource':investigation.target.resource_name,'at':timestamp()}))
    db.commit()

def process_one():
    with SessionLocal() as db:
        row=db.query(OperationRecord).filter_by(kind='job',state='QUEUED').order_by(OperationRecord.created_at).first()
        if not row:return False
        claimed=db.execute(update(OperationRecord).where(OperationRecord.id==row.id,OperationRecord.state=='QUEUED').values(state='RUNNING'))
        db.commit()
        if claimed.rowcount!=1:return True
        token=bound_context.set(row.payload['context'])
        try:
            update_job(db,row,stage='Collecting evidence',started_at=timestamp())
            service=InvestigationService(db,cluster_service=SimpleNamespace(context=row.payload['context']))
            original=service._build_analysis
            def analyze(evidence):
                update_job(db,row,stage='Analyzing evidence')
                return original(evidence)
            service._build_analysis=analyze
            result=service.create(InvestigationCreate.model_validate(row.payload['request']))
            row.state='COMPLETED'
            update_job(db,row,stage='Finished',investigation_id=result.id,investigation_status=result.status.value,finished_at=timestamp())

        except Exception:
            db.rollback();db.refresh(row);row.state='FAILED'
            update_job(db,row,stage='Failed',error='Investigation failed. Check backend diagnostics and retry with a new job.',finished_at=timestamp())
        finally: bound_context.reset(token)
    return True

def _recover_interrupted_jobs():
    with SessionLocal() as db:
        for row in db.query(OperationRecord).filter_by(kind='job', state='RUNNING').all():
            row.state = 'INTERRUPTED'
            p = dict(row.payload)
            p.update(stage='Backend restarted; queue a new investigation.', finished_at=timestamp())
            row.payload = p
        db.commit()


def start_worker():
    global worker, worker_lock
    from app.core.config import BASE_DIR
    with lifecycle_lock:
        if worker and worker.is_alive():
            if stop.is_set():
                raise RuntimeError('Operations worker is still shutting down. Wait for it to finish before restarting.')
            return
        lock = WorkerFileLock(config('OPERATIONS_LOCK_PATH', str(BASE_DIR / '.operations-worker.lock')))
        lock.acquire()
        try:
            # Recovery is only allowed after acquiring exclusive ownership.
            _recover_interrupted_jobs()
            stop.clear()

            def loop():
                try:
                    while not stop.is_set():
                        try:
                            found = process_one()
                        except Exception:
                            found = False
                        if not found:
                            stop.wait(1)
                finally:
                    # Only the exiting worker releases its ownership. Never release
                    # the lock in stop_worker while a job is still running.
                    lock.close()

            thread = Thread(target=loop, name='investigation-worker', daemon=True)
            thread.start()
        except BaseException:
            lock.close()
            worker = None
            worker_lock = None
            raise
        worker = thread
        worker_lock = lock


def stop_worker(timeout=2):
    global worker, worker_lock
    with lifecycle_lock:
        stop.set()
        thread = worker
    if thread:
        thread.join(timeout=timeout)
    with lifecycle_lock:
        if worker is thread and (thread is None or not thread.is_alive()):
            worker = None
            worker_lock = None
