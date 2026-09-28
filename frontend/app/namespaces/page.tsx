"use client";
import { useState } from "react";
import { PageHeading } from "@/components/ui/page-heading";
import { ResourceState } from "@/components/ui/resource-state";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { StatusBadge } from "@/components/ui/status-badge";
import { useNamespaces } from "@/hooks/use-kubernetes";
import { formatAge } from "@/lib/datetime";
export default function NamespacesPage() {
  const namespaces = useNamespaces();
  const [search, setSearch] = useState("");
  const rows = (namespaces.data ?? []).filter(row => row.name.toLowerCase().includes(search.toLowerCase()));
  return <><PageHeading title="Namespaces" description="Namespaces in the active cluster." />
    <div className="rounded-xl border border-border bg-card p-4 space-y-4">
      <input aria-label="Search namespaces" placeholder="Search namespaces…" value={search} onChange={e=>setSearch(e.target.value)} className="w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm" />
      <ResourceState isLoading={namespaces.isLoading} error={namespaces.error} />
      {!namespaces.isLoading && !namespaces.error && <Table paginate><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Status</TableHead><TableHead>Created</TableHead></TableRow></TableHeader><TableBody>{rows.map(row=><TableRow key={row.name}><TableCell className="font-medium">{row.name}</TableCell><TableCell><StatusBadge status={row.status} /></TableCell><TableCell data-sort-value={row.age}>{formatAge(row.age)}</TableCell></TableRow>)}</TableBody></Table>}
      {!namespaces.isLoading && !namespaces.error && !rows.length && <p className="text-sm text-muted-foreground">No namespaces match your search.</p>}
    </div></>;
}
