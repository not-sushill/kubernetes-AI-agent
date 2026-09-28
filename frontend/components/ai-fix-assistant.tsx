"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, errorMessage } from "@/lib/api";
import { useTypedConfirmation } from "@/components/typed-confirmation";
import { DiagnosticChecks } from "@/components/diagnostic-checks";
import { formatDateTime } from "@/lib/datetime";

type Proposal = {
  id: string; state: string; context: string; namespace: string; deployment: string;
  source_proposal_id?: string; diagnostic_run_ids?: string[];
  objective: string; explanation: string; diff?: string; checks: string[];
  evidence_ids: number[]; evidence: {id:number; title:string; evidence:string[]}[];
  confirmation: string; rollback_confirmation: string; result?: string;
  audit: {time:string; event:string}[];
  hypotheses?: {explanation:string;evidence_ids:number[];confidence:string;uncertainty:string;check_id:string}[];
};
const button = "rounded border border-border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40";

export function AiFixAssistant({ investigationId, defaultDeployment = "" }: {investigationId:string; defaultDeployment?:string}) {
  const client = useQueryClient();
  const [deployment,setDeployment] = useState(defaultDeployment);
  const [assessmentOnly,setAssessmentOnly] = useState(true);
  const [objective,setObjective] = useState("");
  const [sourceProposalId,setSourceProposalId]=useState<string|undefined>();
  const [busy,setBusy] = useState("");
  const [error,setError] = useState("");
  const approval = useTypedConfirmation();
  const key = ["fix-proposals",investigationId];
  const proposals = useQuery({queryKey:key,queryFn:()=>apiFetch<Proposal[]>(`/v1/investigations/${encodeURIComponent(investigationId)}/fixes`),refetchInterval:5000});
  const targets = useQuery({queryKey:["fix-targets",investigationId],queryFn:()=>apiFetch<{name:string}[]>(`/v1/investigations/${encodeURIComponent(investigationId)}/fix-targets`),retry:false,staleTime:60000});
  useEffect(()=>{if (!deployment && targets.data?.length===1) setDeployment(targets.data[0].name);},[deployment,targets.data]);
  async function generate() {
    setBusy("generate"); setError("");
    try {
      await apiFetch(`/v1/investigations/${encodeURIComponent(investigationId)}/fixes`, {method:"POST",body:JSON.stringify({deployment,objective,assessment_only:assessmentOnly,source_proposal_id:sourceProposalId})});
      await client.invalidateQueries({queryKey:key});
    } catch(e) {setError(errorMessage(e));} finally {setBusy("");}
  }
  async function reassess(p:Proposal) {
    setBusy(p.id);setError("");
    try {
      await apiFetch(`/v1/investigations/${encodeURIComponent(investigationId)}/fixes`,{method:"POST",body:JSON.stringify({deployment:p.deployment,objective:p.objective,assessment_only:true,source_proposal_id:p.id})});
      await client.invalidateQueries({queryKey:key});
    } catch(e){setError(errorMessage(e));}finally{setBusy("");}
  }
  async function action(p:Proposal, verb:"validate"|"apply"|"rollback") {
    setBusy(p.id); setError("");
    try {
      let confirmation: string | null = null;
      if (verb !== "validate") {
        confirmation = await approval.confirm(verb === "apply" ? p.confirmation : p.rollback_confirmation,
          `${verb === "apply" ? "Apply the reviewed proposal" : "Restore the pre-change Deployment specification"} on ${p.context}, ${p.namespace}/${p.deployment}. This can replace running pods and affect availability.`);
        if (confirmation === null) return;
      }
      await apiFetch(`/v1/fixes/${p.id}/${verb}`, {method:"POST", ...(confirmation !== null ? {body:JSON.stringify({confirmation})} : {})});
    } catch(e) {setError(errorMessage(e));} finally {await client.invalidateQueries({queryKey:key});setBusy("");}
  }
  return <section className="space-y-4 rounded-xl border border-border p-5">
    <div><h2 className="text-lg font-semibold">AI fix assistance</h2>
      <p className="text-sm text-muted-foreground">Generate a proposal, review the diff, validate, then approve. Generation does not change the cluster. All proposed changes are treated as high risk.</p></div>
    <div className="grid gap-3">
      <label className="text-sm">Deployment from this investigation
        <select aria-label="Deployment to fix" className="mt-1 block w-full rounded border bg-background p-2" value={deployment} onChange={e=>{setDeployment(e.target.value);setSourceProposalId(undefined);}}>
          <option value="">{targets.isLoading ? "Resolving Deployment…" : "Select a linked Deployment"}</option>
          {targets.data?.map(t=><option key={t.name} value={t.name}>{t.name}</option>)}
        </select></label>
      {sourceProposalId && <p className="text-sm">Using fresh diagnostic results from {sourceProposalId}. <button className={button} onClick={()=>setSourceProposalId(undefined)}>Clear source</button></p>}
      <label className="text-sm">What should change? Include facts you have verified.
        <textarea aria-label="Fix objective" className="mt-1 block w-full rounded border bg-background p-2" rows={3} maxLength={2000} value={objective} onChange={e=>setObjective(e.target.value)} placeholder="Describe the issue and a verified correction, if known. The assistant will ask for missing facts rather than guess." /></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={assessmentOnly} onChange={e=>setAssessmentOnly(e.target.checked)} />Assessment only — explain evidence and checks; no change proposals</label>
      <p className="text-xs text-muted-foreground">Uncheck only when you want a reviewed fix proposal and can supply the facts needed for a specific change.</p>
      <p className="text-xs text-muted-foreground">Supported: regular and init-container images, CPU/memory requests and limits, replicas, and existing probe paths, ports and timing. Do not enter credentials.</p>
      <button className={button} disabled={!!busy || !targets.data?.some(t=>t.name===deployment) || !deployment.trim() || objective.trim().length<10} onClick={generate}>{busy === "generate" ? "Generating…" : assessmentOnly ? "Assess with AI" : "Generate AI fix proposal"}</button>
    </div>
    {targets.error ? <p role="alert" className="text-sm text-destructive">{errorMessage(targets.error)} Run a fresh Deployment investigation if ownership cannot be resolved.</p> : null}
    {targets.data?.length===0 && <p className="text-sm">No linked Deployment is available. Investigate the owning Deployment first; other workload kinds are not supported here.</p>}
    {error || proposals.error ? <p role="alert" className="text-sm text-destructive">{error || errorMessage(proposals.error)}</p> : null}
    {proposals.isLoading ? <p>Loading saved proposals…</p> : null}
    {proposals.data?.map(p=><article key={p.id} className="space-y-3 rounded-lg border border-border p-4">
      <div className="flex flex-wrap justify-between gap-2"><strong>{p.deployment}</strong><span>{p.state}</span></div>
      <p className="break-all text-xs">Context: {p.context} · Namespace: {p.namespace} · Proposal: {p.id}</p>
      <p className="text-sm"><strong>Objective:</strong> {p.objective}</p>
      <p className="text-sm">{p.explanation}</p>
      {p.evidence.filter(e=>p.evidence_ids.includes(e.id)||p.hypotheses?.some(h=>h.evidence_ids.includes(e.id))).map(e=><details key={e.id}><summary className="text-sm">Supporting evidence #{e.id}: {e.title}</summary><pre className="whitespace-pre-wrap break-words text-xs">{e.evidence.join("\n")}</pre></details>)}
      {p.hypotheses?.length ? <div className="space-y-2"><h3 className="font-semibold">Evidence-based reasoning</h3>{p.hypotheses.map((h,i)=><div key={i} className="rounded bg-muted p-3 text-sm"><p>{h.explanation}</p><p>Confidence: {h.confidence} · Evidence: {h.evidence_ids.map(id=>`#${id}`).join(", ")||"No supporting evidence cited"}</p><p>Uncertainty: {h.uncertainty}</p><p>Suggested check: {h.check_id.replaceAll("_"," ")}</p></div>)}</div> : null}
      <DiagnosticChecks recommended={p.hypotheses?.map(h=>h.check_id)} proposalId={p.id} disabled={!!busy} onReassess={()=>reassess(p)} hasInheritedResults={!!p.diagnostic_run_ids?.length} onPrepareFix={()=>{setDeployment(p.deployment);setObjective(p.objective);setAssessmentOnly(false);setSourceProposalId(p.source_proposal_id||p.id);window.scrollTo({top:0,behavior:"smooth"});}} />
      {p.checks.length>0 && <ul className="list-disc pl-5 text-sm">{p.checks.map((c,i)=><li key={i}>{c}</li>)}</ul>}
      {p.diff && <div><h3 className="font-medium">Review YAML diff</h3><p className="text-xs text-muted-foreground">Only editable fields are shown; other Deployment fields are preserved.</p><pre className="max-h-96 overflow-auto rounded bg-muted p-3 text-xs">{p.diff}</pre></div>}
      {p.result && <p role="status" className="rounded bg-muted p-3 text-sm">{p.result}</p>}
      <div className="flex flex-wrap gap-2">
        {["PROPOSED","VALIDATED"].includes(p.state) && <button className={button} disabled={!!busy} onClick={()=>action(p,"validate")}>Validate with Kubernetes</button>}
        {p.state === "VALIDATED" && <button className={button} disabled={!!busy} onClick={()=>action(p,"apply")}>Review approval and apply</button>}
        {["APPLIED","APPLIED_UNCONFIRMED"].includes(p.state) && <button className={button} disabled={!!busy} onClick={()=>action(p,"rollback")}>Review rollback approval</button>}
        {p.diff && <button className={button} onClick={async()=>{try{const text=await apiFetch<string>(`/v1/fixes/${p.id}/backup`);const url=URL.createObjectURL(new Blob([text],{type:'text/yaml'}));const a=document.createElement('a');a.href=url;a.download=`recovery-${p.id}.yaml`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){setError(errorMessage(e));}}}>Download recovery YAML</button>}
      </div>
      {busy===p.id && <p role="status" className="text-sm">Operation in progress… Application verification may take up to a minute.</p>}
      {["APPLYING","ROLLING_BACK","OUTCOME_UNKNOWN"].includes(p.state) && <p className="text-sm">Do not resubmit this change. Check live Deployment state. If the backend stopped during the operation, use the recovery YAML for a reviewed manual restore.</p>}
      <details><summary className="text-sm">Operation history</summary><ul className="space-y-1 text-xs">{p.audit.map((a,i)=><li key={i}>{formatDateTime(a.time)} — {a.event}</li>)}</ul></details>
    </article>)}
    {approval.dialog}
  </section>;
}
