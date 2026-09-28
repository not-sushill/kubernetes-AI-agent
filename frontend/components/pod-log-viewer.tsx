"use client";
import { Fragment, useEffect, useMemo, useState } from "react";
import type { LogOptions, PodLogs } from "@/hooks/use-kubernetes";
import { errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/datetime";
import { highlightLogText, istLogStart, searchLogs } from "@/lib/log-search";
const input="rounded-md border border-border bg-background px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring";
export function PodLogViewer({options,onLoad,data,loading,error}:{options:LogOptions;onLoad:(value:LogOptions)=>void;data?:PodLogs;loading:boolean;error:unknown}) {
  const [range,setRange]=useState(options.since_time ? "custom" : options.since || "all");
  const [start,setStart]=useState("");
  const [tail,setTail]=useState(options.tail);
  const [container,setContainer]=useState(options.container || "");
  const [previous,setPrevious]=useState(!!options.previous);
  const [query,setQuery]=useState("");const [errorsOnly,setErrorsOnly]=useState(false);
  const [caseSensitive,setCaseSensitive]=useState(false);const [context,setContext]=useState(2);
  const [onlyMatches,setOnlyMatches]=useState(false);
  const [page,setPage]=useState(0);
  const [wrap,setWrap]=useState(false);
  const [localError,setLocalError]=useState("");
  const filtered=useMemo(()=>searchLogs(data?.logs||[],query,errorsOnly,caseSensitive,query||errorsOnly ? context : 0),[data,query,errorsOnly,caseSensitive,context]);
  const rows=useMemo(()=>onlyMatches ? filtered.rows : (data?.logs||[]).map((line,i)=>({number:i+1,line})),[onlyMatches,filtered,data]);
  useEffect(()=>setPage(0),[query,errorsOnly,caseSensitive,context,onlyMatches,data]);
  const pages=Math.max(1,Math.ceil(rows.length/500));
  const currentPage=Math.min(page,pages-1);
  const visible=rows.slice(currentPage*500,(currentPage+1)*500);
  const timestamp=(line:string)=>{const value=line.split(" ")[0];return /^\d{4}-\d{2}-\d{2}T/.test(value)&&!Number.isNaN(Date.parse(value)) ? formatDateTime(value) : "unavailable";};
  function load(){try{setLocalError("");onLoad({tail,container:container.trim()||undefined,previous,...(range==="custom" ? {since_time:istLogStart(start)} : range==="all" ? {} : {since:range})});}catch(e){setLocalError(errorMessage(e));}}
  function download(){const blob=new Blob([rows.map(r=>r.line).join("\n")],{type:"text/plain;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=`${data?.pod||"pod"}-filtered.log`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return <div className="space-y-3">
    <div className="space-y-3 border-b border-border pb-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="grid flex-1 gap-1.5 text-xs font-medium text-muted-foreground">Time window
          <select className={`${input} min-w-48 text-foreground`} value={range} onChange={e=>setRange(e.target.value)}><option value="all">Latest retained logs</option>{["1h","6h","12h","24h","48h","168h"].map(v=><option key={v} value={v}>Last {v==="168h" ? "7 days" : v}</option>)}<option value="custom">Since specific time (IST)</option></select>
        </label>
        {range==="custom" && <label className="grid gap-1.5 text-xs font-medium">From (IST)<input className={input} type="datetime-local" value={start} onChange={e=>setStart(e.target.value)} /></label>}
        <button className="rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50" disabled={loading} onClick={load}>{loading ? "Fetching…" : "Load logs"}</button>
        <button className={input} disabled={!rows.length} onClick={download}>Download logs</button>
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">Settings{previous ? " · previous instance" : ""} · {tail.toLocaleString()} lines</summary>
        <div className="mt-3 flex flex-wrap items-end gap-4">
          <label className="grid gap-1 text-xs">Maximum lines<select className={input} value={tail} onChange={e=>setTail(Number(e.target.value))}>{[200,1000,5000,10000,50000,100000].map(v=><option key={v} value={v}>{v.toLocaleString()}</option>)}</select></label>
          <label className="grid gap-1 text-xs">Container (optional)<input className={input} value={container} placeholder="Default container" onChange={e=>setContainer(e.target.value)} /></label>
          <label className="flex items-center gap-2 py-2"><input type="checkbox" checked={previous} onChange={e=>setPrevious(e.target.checked)} /> Previous container instance</label>
          <button className={input} disabled={loading} onClick={()=>{setLocalError("");setRange("all");setPrevious(false);setContainer("");setQuery("");setErrorsOnly(false);setOnlyMatches(false);setTail(5000);onLoad({tail:5000,previous:false});}}>Reset to current logs</button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Use Load logs to apply settings.</p>
      </details>
    </div>
    {localError || error ? <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{localError || errorMessage(error)}</p> : null}
    {data?.available===false && <div role="alert" className="rounded-lg border border-border p-3 text-sm space-y-2"><p>Logs unavailable: {data.message || "The requested container logs are not retained or could not be read."}</p>{options.previous && <button className={input} disabled={loading} onClick={()=>{setPrevious(false);onLoad({...options,previous:false});}}>Load current container logs</button>}</div>}
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-3">
        <input className={`${input} min-w-0 w-full flex-1 sm:min-w-64`} aria-label="Search fetched logs" placeholder="Search logs…" value={query} onChange={e=>setQuery(e.target.value)} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={wrap} onChange={e=>setWrap(e.target.checked)} /> Wrap lines</label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={onlyMatches} onChange={e=>setOnlyMatches(e.target.checked)} /> Show matching lines only</label>
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Filters{errorsOnly ? " · error keywords" : ""}{caseSensitive ? " · case sensitive" : ""}</summary>
        <div className="mt-3 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2"><input type="checkbox" checked={errorsOnly} onChange={e=>setErrorsOnly(e.target.checked)} /> Error keywords</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={caseSensitive} onChange={e=>setCaseSensitive(e.target.checked)} /> Case sensitive</label>
          <label>Context lines <select className={input} value={context} onChange={e=>setContext(Number(e.target.value))}>{[0,2,5,10].map(v=><option key={v}>{v}</option>)}</select></label>
          <button className={input} onClick={()=>{setQuery("");setErrorsOnly(false);setCaseSensitive(false);setOnlyMatches(false);setPage(0);}}>Show all fetched logs</button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Search applies to loaded logs. Download includes all matching pages.</p>
      </details>
    </div>
    {data && <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-muted-foreground"><span>{data.line_count.toLocaleString()} lines loaded{(query || errorsOnly) && <> · {filtered.matches.length.toLocaleString()} matches</>}{onlyMatches && <> · {rows.length.toLocaleString()} with context</>}</span>{data.logs.length>0 && <span>{timestamp(data.logs[0])} — {timestamp(data.logs[data.logs.length-1])}</span>}</div>}
    {data && data.line_count>=options.tail && <p className="rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">Line limit reached. Increase the limit in Settings for older retained logs.</p>}
    {data && onlyMatches && !filtered.rows.length && data.available!==false && <p className="p-3 text-sm">No matching lines in the fetched logs. This does not establish that no errors occurred.</p>}
    {!data && !loading && !error && <p className="p-3 text-sm">No log response loaded yet. Click Load logs.</p>}
    {loading && <p role="status" className="text-sm">Fetching logs…</p>}
    {data && data.logs.length===0 && data.available!==false && <p className="p-3 text-sm">No lines were returned for this request. Try another time window or container.</p>}
    <pre aria-label="Pod log contents" tabIndex={0} className={`log-content ${wrap ? "log-wrap" : ""}`}>{query || errorsOnly ? visible.map((r,i)=><Fragment key={r.number}>{i>0 ? "\n" : ""}{i>0&&r.number>visible[i-1].number+1 ? "…\n" : ""}<span className="log-line-number select-none">{r.number}  </span>{highlightLogText(r.line,query,caseSensitive,errorsOnly).map((part,n)=>part.highlight ? <mark key={n} className="rounded-sm bg-yellow-300 text-slate-950 dark:bg-amber-300 dark:text-slate-950">{part.text}</mark> : <Fragment key={n}>{part.text}</Fragment>)}</Fragment>) : visible.map(r=>`${r.number}  ${r.line}`).join("\n")}</pre>
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <span className="text-xs text-muted-foreground">Page {currentPage+1} of {pages} · 500 lines per page</span>
      <div className="flex gap-2"><button className={input} disabled={currentPage===0} onClick={()=>setPage(currentPage-1)}>Previous page</button><button className={input} disabled={currentPage+1>=pages} onClick={()=>setPage(currentPage+1)}>Next page</button></div>
    </div>
    <details className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground">
      <summary className="cursor-pointer">Details</summary>
      <p className="mt-2">Loaded request: {options.previous ? "Previous container instance" : "Current container instance"} · {options.container || "Default container"} · {options.since_time ? `Since ${formatDateTime(options.since_time)}` : options.since ? `Last ${options.since}` : "No time cutoff"} · maximum {options.tail.toLocaleString()} lines</p>
      <p className="mt-2">Kubernetes logs are not an archive: rotated logs and deleted pods may be unavailable. Use a central log archive for older records. The fetched range is shown in IST; raw log timestamps are preserved.</p>
    </details>
  </div>;
}
