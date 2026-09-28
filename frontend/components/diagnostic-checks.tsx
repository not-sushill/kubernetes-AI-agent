"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/datetime";
type Check={id:string;title:string;purpose:string;commands:string[][]};
type Run={id:string;title:string;state:string;output?:string;finished_at?:string;started_at:string;truncated?:boolean;executed_commands:string[][]};
const button="rounded border border-border px-3 py-2 text-sm disabled:opacity-40";
function commandText(args:string[]){return args.map(x=>/^[a-zA-Z0-9_./:=,@-]+$/.test(x)?x:"'"+x.replace(/'/g,"''")+"'").join(' ');}
export function DiagnosticChecks({proposalId,onReassess,onPrepareFix,hasInheritedResults,disabled,recommended=[]}:{proposalId:string;onReassess:(id:string)=>Promise<void>;onPrepareFix:()=>void;hasInheritedResults:boolean;disabled:boolean;recommended?:string[]}) {
 const client=useQueryClient();const [busy,setBusy]=useState("");const [error,setError]=useState("");
 const catalog=useQuery({queryKey:['diagnostic-checks',proposalId],queryFn:()=>apiFetch<Check[]>(`/v1/fixes/${proposalId}/diagnostic-checks`)});
 const runs=useQuery({queryKey:['diagnostic-runs',proposalId],queryFn:()=>apiFetch<Run[]>(`/v1/fixes/${proposalId}/diagnostic-runs`),refetchInterval:5000});
 async function run(id:string){setBusy(id);setError("");try{await apiFetch(`/v1/fixes/${proposalId}/diagnostic-runs`,{method:'POST',body:JSON.stringify({check_id:id})});}catch(e){setError(errorMessage(e));}finally{await client.invalidateQueries({queryKey:['diagnostic-runs',proposalId]});setBusy("");}}
 return <section className="space-y-3 rounded border border-border p-3">
  <h3 className="font-semibold">Read-only diagnostic commands</h3>
  <p className="text-xs text-muted-foreground">Checks use the saved cluster context and verify the Deployment identity. Pod and event results are filtered by owner UID. No changes are applied.</p>
  {catalog.data?.slice().sort((a,b)=>Number(recommended.includes(b.id))-Number(recommended.includes(a.id))).map(c=><details key={c.id}><summary>{c.title}{recommended.includes(c.id) ? " · Suggested by assessment" : ""}</summary><p className="text-sm">{c.purpose}</p><pre className="overflow-auto rounded bg-muted p-2 text-xs">{c.commands.map(commandText).join('\n')}</pre><button className={button} disabled={disabled||!!busy} onClick={()=>run(c.id)}>{busy===c.id?'Running…':'Run read-only check'}</button></details>)}
  {error||catalog.error||runs.error ? <p role="alert" className="text-destructive">{error||errorMessage(catalog.error||runs.error)}</p>:null}
  {runs.data?.map(r=><details key={r.id}><summary>{r.title} · {r.state} · {formatDateTime(r.finished_at||r.started_at)}</summary>
   <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-xs">{r.output||'No output saved yet. A backend interruption may leave this read-only check unfinished; it can be run again.'}</pre>
   {r.truncated&&<p className="text-xs">Output is truncated; this sample is not complete evidence.</p>}
   <pre className="overflow-auto text-xs">{r.executed_commands.map(commandText).join('\n')}</pre>
  </details>)}
  <button className={button} disabled={disabled||!!busy||!runs.data?.some(r=>r.state==='COMPLETED')} onClick={()=>onReassess(proposalId)}>Reassess with check results</button>
  <button className={button} disabled={disabled||!!busy||(!hasInheritedResults&&!runs.data?.some(r=>r.state==='COMPLETED'))} onClick={onPrepareFix}>Prepare fix using these checks</button>
  <p className="text-xs text-muted-foreground">Reassessment creates a separate assessment, using successful checks from the last 15 minutes only if the Deployment spec still matches. It does not approve or apply a fix.</p>
 </section>;
}
