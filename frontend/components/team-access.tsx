"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
export function TeamAccess(){
 const [token,setToken]=useState("");const client=useQueryClient();
 function save(){sessionStorage.setItem('agent-api-token',token);setToken('');client.clear();window.location.reload();}
 function clear(){sessionStorage.removeItem('agent-api-token');client.clear();window.location.reload();}
 return <details className="relative text-sm"><summary className="cursor-pointer text-white">Access</summary><div className="absolute right-0 z-50 mt-3 w-72 space-y-3 rounded-xl border bg-card p-4 text-card-foreground shadow-lg"><label className="grid gap-2">API token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)} className="rounded border bg-background p-2" /></label><div className="flex gap-3"><button disabled={!token} onClick={save} className="rounded bg-primary px-3 py-2 text-primary-foreground disabled:opacity-50">Sign in</button><button onClick={clear}>Sign out</button></div><p className="text-xs text-muted-foreground">Required only when team access is enabled. Stored in this tab.</p></div></details>;
}
