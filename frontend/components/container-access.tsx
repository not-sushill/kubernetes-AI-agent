"use client";

import { useEffect, useRef, useState } from "react";
import { accessHeaders, API_BASE_URL, apiFetch, responseErrorMessage } from "@/lib/api";
import { TerminalView, type TerminalHandle } from "@/components/terminal-view";
import { useTypedConfirmation } from "@/components/typed-confirmation";

type Info = { context: string; namespace: string; pod: string; uid: string; containers: {name: string; running: boolean}[] };
const root = "/kubernetes/container-access";
const maxBytes = 16 * 1024 * 1024;

export function ContainerAccess({namespace, pod}: {namespace: string; pod: string}) {
  const [info, setInfo] = useState<Info | null>(null);
  const [container, setContainer] = useState("");
  const [shell, setShell] = useState("/bin/sh");
  const [status, setStatus] = useState("Disconnected");
  const [terminalReady, setTerminalReady] = useState(false);
  const [inputState, setInputState] = useState("No input sent");
  const sessionReady = useRef(false);
  const [path, setPath] = useState("/tmp/report.txt");
  const [file, setFile] = useState<File | null>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const mounted = useRef(true);
  const connectionVersion = useRef(0);
  const terminal = useRef<TerminalHandle>(null);
  const {confirm, dialog} = useTypedConfirmation();
  const target = info ? {context: info.context, namespace: info.namespace, pod: info.pod, uid: info.uid, container} : null;
  const running = info?.containers.some(c => c.name === container && c.running);
  const locked = connecting || connected;
  const inputClass = "rounded border border-border bg-background px-3 py-2 text-sm";
  const buttonClass = "rounded border border-border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40";

  useEffect(() => {
    mounted.current = true;
    connectionVersion.current++;
    const controller = new AbortController();
    apiFetch<Info>(`${root}/${encodeURIComponent(namespace)}/${encodeURIComponent(pod)}`, {signal: controller.signal})
      .then(data => {setInfo(data); setContainer(data.containers.find(c => c.running)?.name || "");})
      .catch(error => {if (!controller.signal.aborted) setMessage(error.message);});
    return () => {mounted.current = false; controller.abort(); socket.current?.close();};
  }, [namespace, pod]);

  function append(text: string) {terminal.current?.write(text);}
  function sendInput(data: string) {
    if (!sessionReady.current || socket.current?.readyState !== WebSocket.OPEN) return;
    setInputState("Input sent; waiting for PTY acknowledgement");
    // Preserve raw keys, including Tab, arrows and Ctrl+C; split large pasted input.
    const characters = Array.from(data);
    for (let start = 0; start < characters.length; start += 4096) {
      socket.current.send(JSON.stringify({type: "input", data: characters.slice(start, start + 4096).join("")}));
    }
  }
  function resize(rows: number, cols: number) {
    if (socket.current?.readyState === WebSocket.OPEN && connected) {
      socket.current.send(JSON.stringify({type: "resize", rows: Math.min(200, Math.max(2, rows)), cols: Math.min(500, Math.max(2, cols))}));
    }
  }
  function disconnect() {
    connectionVersion.current++;
    sessionReady.current = false;
    socket.current?.close(); socket.current = null;
    setConnected(false); setConnecting(false); setStatus("Disconnected");
  }
  async function connect() {
    if (!target || !running || locked || !terminalReady) return;
    const expected = `EXEC ${target.context} ${namespace}/${pod}/${container}`;
    const approval = await confirm(expected, "Open a shell with your Kubernetes permissions. Commands can modify this container; Apply approval does not govern shell commands. No per-command confirmation is shown.");
    if (approval !== expected || !mounted.current) return;
    const version = ++connectionVersion.current;
    sessionReady.current = false; setInputState("No input sent");
    setConnecting(true); setMessage(""); terminal.current?.clear(); setStatus("Connecting…");
    try {
      const result = await apiFetch<{ticket: string}>(`${root}/terminal`, {method: "POST", body: JSON.stringify({...target, shell, confirmation: approval})});
      if (!mounted.current || version !== connectionVersion.current) return;
      const url = new URL(API_BASE_URL.replace(/\/$/, "") + root + "/terminal/ws", window.location.href);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(url);
      socket.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ticket: result.ticket, ...terminal.current?.size()}));
      ws.onmessage = event => {
        if (!mounted.current || version !== connectionVersion.current) return;
        const data = JSON.parse(event.data);
        if (data.type === "input_ack") setInputState("Input accepted by PTY");
        if (data.type === "ready") {sessionReady.current = true; setConnecting(false); setConnected(true); setStatus("Connected"); terminal.current?.focus();}
        if (data.type === "output") append(data.data);
        if (data.type === "error") {setMessage(data.message); append(`\r\n${data.message}\n`);}
        if (data.type === "exit") append(`\r\nShell exited (${data.code}).\n`);
      };
      ws.onerror = () => setMessage("Terminal connection failed. Check backend availability and WebSocket support.");
      ws.onclose = () => {if (socket.current === ws) {socket.current = null; sessionReady.current = false; setConnecting(false); setConnected(false); setStatus("Disconnected");}};
    } catch (error) {if (!mounted.current || version !== connectionVersion.current) return; setMessage(error instanceof Error ? error.message : "Connection failed"); setConnecting(false); setStatus("Disconnected");}
  }
  async function transfer(upload: boolean) {
    if (!target || !running) return;
    const destination = path;
    const selectedFile = file;
    if (upload && (!selectedFile || selectedFile.size > maxBytes)) {setMessage("Choose a file no larger than 16 MiB."); return;}
    let approval: string | null = null;
    if (upload) {
      const expected = `UPLOAD ${target.context} ${namespace}/${pod}/${container} ${destination}`;
      approval = await confirm(expected, `Upload ${selectedFile!.name} to ${destination}. ${overwrite ? "Overwrite is enabled: an existing file will be replaced." : "An existing file will be refused."}`);
      if (approval !== expected || !mounted.current) return;
    }
    setBusy(true); setMessage("");
    try {
      let body: BodyInit;
      const headers: Record<string,string> = {};
      if (upload) {
        const form = new FormData(); form.set("target", JSON.stringify(target)); form.set("path", destination);
        form.set("confirmation", approval!); form.set("overwrite", String(overwrite)); form.set("file", selectedFile!); body = form;
      } else {body = JSON.stringify({...target, path: destination}); headers["Content-Type"] = "application/json";}
      const result = await fetch(API_BASE_URL.replace(/\/$/, "") + root + (upload ? "/upload" : "/download"), {method: "POST", headers: {...headers,...accessHeaders()}, body});
      if (!result.ok) {
        const error = await result.json().catch(() => null);
        throw new Error(responseErrorMessage(error) || `Transfer failed (${result.status})`);
      }
      if (upload) {setMessage((await result.json()).message);} else {
        const blob = await result.blob(); const url = URL.createObjectURL(blob);
        const link = document.createElement("a"); link.href = url; link.download = destination.split("/").pop() || "download";
        link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); setMessage("Download completed.");
      }
    } catch (error) {setMessage(error instanceof Error ? error.message : "Transfer failed");}
    finally {setBusy(false);}
  }
  return <section className="my-6 space-y-4 rounded-xl border border-border bg-card p-5">
    {dialog}
    <h2 className="text-lg font-semibold">Container terminal and files</h2>
    <p className="break-all text-sm">{info ? `${info.context} · ${namespace}/${pod}` : "Loading container target…"}</p>
    <div className="flex flex-wrap items-center gap-3">
      <label>Container <select aria-label="Container" className={inputClass} value={container} disabled={locked || busy} onChange={e => setContainer(e.target.value)}>
        <option value="">Select container</option>{info?.containers.map(c => <option key={c.name} value={c.name} disabled={!c.running}>{c.name}{c.running ? "" : " (not running)"}</option>)}
      </select></label>
      <label>Shell <select aria-label="Shell" className={inputClass} value={shell} disabled={locked} onChange={e => setShell(e.target.value)}><option>/bin/sh</option><option>/bin/bash</option></select></label>
      <button className={buttonClass} disabled={!running || locked || !terminalReady} onClick={connect}>Open terminal</button>
      <button className={buttonClass} disabled={!locked} onClick={disconnect}>Disconnect</button>
      <button className={buttonClass} disabled={!connected} onClick={() => terminal.current?.focus()}>Focus terminal</button>
      <span role="status">{status}</span>
      {connected && <span className="text-xs text-muted-foreground" role="status">{inputState}</span>}
    </div>
    <p className="text-sm text-muted-foreground">Click inside the terminal to type. Tab completion, arrow keys and Ctrl+C are sent to the container shell. Choose /bin/bash if installed for Bash completion. Shift+Escape moves focus out of the terminal. Idle timeout: 5 minutes.</p>
    <TerminalView ref={terminal} enabled={connected} onInput={sendInput} onResize={resize}
      onReady={() => setTerminalReady(true)} onError={setMessage} />
    <h3 className="font-semibold">File transfer</h3>
    <p className="text-sm text-muted-foreground">One file, up to 16 MiB. Download requires cat; upload requires /bin/sh and cat. The destination directory must already exist.</p>
    <label className="block">Container file path <input className={`${inputClass} mt-1 block w-full`} value={path} disabled={busy} onChange={e => setPath(e.target.value)} /></label>
    <div className="flex flex-wrap items-center gap-3">
      <button className={buttonClass} disabled={!running || busy || !path} onClick={() => transfer(false)}>Download file</button>
      <input aria-label="Local file" type="file" disabled={busy} onChange={e => setFile(e.target.files?.[0] || null)} />
      <label className="text-sm"><input type="checkbox" checked={overwrite} disabled={busy} onChange={e => setOverwrite(e.target.checked)} /> Allow overwrite</label>
      <button className={buttonClass} disabled={!running || busy || !file || !path} onClick={() => transfer(true)}>Upload file</button>
    </div>
    {busy && <p role="status">Transferring file…</p>}
    {message && <p role="status" className="whitespace-pre-wrap break-words rounded border border-border p-3">{message}</p>}
  </section>;
}
