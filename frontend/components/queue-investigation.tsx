"use client";
import { useState } from 'react';
import Link from 'next/link';
import { apiFetch,errorMessage } from '@/lib/api';
export function QueueInvestigation({namespace,resourceType,resourceName}:{namespace:string;resourceType:string;resourceName?:string}){
 const [busy,setBusy]=useState(false);const [queued,setQueued]=useState(false);const [error,setError]=useState('');
 async function queue(){setBusy(true);setError('');try{const c=await apiFetch<{current_context:string}>('/kubernetes/contexts');await apiFetch('/v1/operations/jobs',{method:'POST',body:JSON.stringify({context:c.current_context,namespace,resource_type:resourceType,resource_name:resourceName,log_tail:200})});setQueued(true);}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}
 return <span className="inline-flex flex-col gap-1">{queued?<Link className="text-xs text-primary" href="/operations">View queued job →</Link>:<button title="Run in the background; results survive navigation" className="rounded-md border px-2 py-1 text-xs disabled:opacity-40" disabled={busy} onClick={queue}>{busy?'Queuing…':'Queue'}</button>}{error&&<span role="alert" className="text-xs text-destructive">{error}</span>}</span>;
}
