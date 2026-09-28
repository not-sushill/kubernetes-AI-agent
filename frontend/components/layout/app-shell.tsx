"use client";

import { Activity, Boxes, LayoutDashboard, Layers, Network, SearchCheck, Server, Waypoints } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, type ChangeEvent } from "react";
import { TeamAccess } from "@/components/team-access";
import { ThemeToggle } from "@/components/theme-toggle";
import { useKubernetesContexts, useSwitchKubernetesContext } from "@/hooks/use-kubernetes";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/namespaces", label: "Namespaces", icon: Layers },
  { href: "/pods", label: "Pods", icon: Boxes },
  { href: "/deployments", label: "Deployments", icon: Activity },
  { href: "/services", label: "Services", icon: Network },
  { href: "/ingresses", label: "Ingresses", icon: Waypoints },
  { href: "/nodes", label: "Nodes", icon: Server },
  { href: "/operations", label: "Operations", icon: Activity },
  { href: "/investigations", label: "Investigations", icon: SearchCheck },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const contexts = useKubernetesContexts();
  const switchContext = useSwitchKubernetesContext();
  const currentContext = contexts.data?.current_context ?? "";
  const page = navItems.find(item => item.href !== "/" && pathname.startsWith(item.href))?.label ?? "Dashboard";
  function changeContext(event: ChangeEvent<HTMLSelectElement>) {
    if (event.target.value && event.target.value !== currentContext) {
      switchContext.mutate({ context: event.target.value });
    }
  }
  return (
    <div className="min-h-screen bg-background">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-card focus:p-3">Skip to content</a>
      <header className="sticky top-0 z-30 shadow-sm">
        <div className="brand-header flex min-h-16 flex-wrap items-center justify-between gap-3 px-5 py-3 lg:px-8">
          <div className="flex items-center gap-5">
            <Link href="/" className="leading-tight text-white">
              <span className="block text-xl font-bold tracking-tight">AI Kubernetes</span>
              <span className="block text-right text-xs font-semibold text-sky-300">Investigation Console</span>
            </Link>
            <span className="hidden h-7 w-px bg-white/25 sm:block" />
            <div className="hidden items-center gap-2 text-sm font-medium text-white sm:flex">
              <Network className="h-4 w-4" aria-hidden="true" />
              <span>Cluster console</span><span className="mx-2 text-white/50">/</span><span>{page}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <TeamAccess />
            <div className="rounded-md bg-white text-slate-800 dark:bg-slate-800 dark:text-white"><ThemeToggle /></div>
          </div>
        </div>
        <div className="border-b border-border bg-card px-4 lg:px-8">
          <nav aria-label="Main navigation" className="flex gap-1 overflow-x-auto">
            {navItems.map(item => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              const Icon = item.icon;
              return <Link key={item.href} href={item.href} target="_blank" rel="noopener noreferrer" title={`${item.label} — opens in a new tab`} aria-current={active ? "page" : undefined}
                className={cn("flex shrink-0 items-center gap-2 border-b-2 border-transparent px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground", active && "border-primary text-primary bg-primary/5")}>
                <Icon className="h-4 w-4" aria-hidden="true" />{item.label}
              </Link>;
            })}
          </nav>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-[1600px] px-4 py-5 lg:px-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2"><Network className="h-4 w-4 text-primary" /><p className="text-sm font-medium">Cluster</p></div>
          <div className="w-full sm:w-auto sm:max-w-[65%]">
            <label className="sr-only" htmlFor="active-cluster">Active Kubernetes cluster</label>
            <select id="active-cluster" value={currentContext} onChange={changeContext}
              disabled={contexts.isLoading || contexts.isError || switchContext.isPending}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring disabled:opacity-50">
              {contexts.isLoading ? <option value="">Loading clusters…</option> :
                contexts.isError ? <option value="">Unable to load clusters</option> :
                !contexts.data?.contexts.length ? <option value="">No contexts available</option> :
                contexts.data.contexts.map(context => <option key={context} value={context}>{context}</option>)}
            </select>
            {switchContext.isPending && <p className="mt-1 text-xs text-muted-foreground" role="status">Switching cluster…</p>}
            {switchContext.isError && <p className="mt-1 text-xs text-destructive" role="alert">Failed to switch cluster.</p>}
          </div>
        </div>
        <div className="page-enter" key={pathname}>{children}</div>
      </main>
    </div>
  );
}
