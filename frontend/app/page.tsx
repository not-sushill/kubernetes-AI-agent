"use client";

import { Activity, Boxes, Gauge, Layers, Server } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeading } from "@/components/ui/page-heading";
import { ResourceState } from "@/components/ui/resource-state";
import { useNodes } from "@/hooks/use-kubernetes";
import { ClusterScore } from "@/components/dashboard/cluster-score";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  useClusterHealth,
  useDeployments,
  useNamespaces,
  usePods,
} from "@/hooks/use-kubernetes";

export default function DashboardPage() {
  const cluster = useClusterHealth();
  const namespaces = useNamespaces();
  const pods = usePods();
  const deployments = useDeployments();
  const nodes = useNodes();

  const podHealth = useMemo(() => {
    const rows = pods.data ?? [];

    const running = rows.filter(
      (pod) => pod.status === "Running",
    ).length;

    const restarts = rows.reduce(
      (total, pod) => total + pod.restarts,
      0,
    );

    return {
      total: rows.length,
      running,
      restarts,
    };
  }, [pods.data]);

  const deploymentHealth = useMemo(() => {
    const rows = deployments.data ?? [];

    const ready = rows.filter(
      (deployment) =>
        deployment.replicas > 0 &&
        deployment.ready_replicas === deployment.replicas,
    ).length;

    return {
      total: rows.length,
      ready,
    };
  }, [deployments.data]);

  const nodeHealth = useMemo(() => {
    const rows = nodes.data ?? [];

    const ready = rows.filter(
      (node) => node.status === "Ready",
    ).length;

    return {
      total: rows.length,
      ready,
    };
  }, [nodes.data]);

  const clusterScore = useMemo(() => {
    const podScore =
      podHealth.total === 0
        ? 100
        : (podHealth.running / podHealth.total) * 100;

    const deploymentScore =
      deploymentHealth.total === 0
        ? 100
        : (deploymentHealth.ready /
          deploymentHealth.total) *
        100;

    const nodeScore =
      nodeHealth.total === 0
        ? 100
        : (nodeHealth.ready /
          nodeHealth.total) *
        100;

    return Math.round(
      (podScore +
        deploymentScore +
        nodeScore) /
      3,
    );
  }, [
    podHealth,
    deploymentHealth,
    nodeHealth,
  ]);

  const firstError =
    cluster.error ?? namespaces.error ?? pods.error ?? deployments.error;

  return (
    <>
      <PageHeading
        title="Dashboard"
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Link href="/namespaces" target="_blank" rel="noopener noreferrer" title="Namespaces — opens in a new tab" className="group rounded-xl outline-none transition-transform motion-safe:hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-ring">
        <MetricCard
          title="Namespaces"
          value={namespaces.data?.length ?? 0}
          icon={Layers}
          detail={namespaces.isFetching ? "refreshing" : "current"}
        />
        </Link>
        <Link href="/pods" target="_blank" rel="noopener noreferrer" title="Pods — opens in a new tab" className="group rounded-xl outline-none transition-transform motion-safe:hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-ring">
        <MetricCard
          title="Pods"
          value={podHealth.total}
          icon={Boxes}
          tone={podHealth.total === podHealth.running ? "success" : "warning"}
          detail={`${podHealth.running} running`}
        />
        </Link>
        <Link href="/deployments" target="_blank" rel="noopener noreferrer" title="Deployments — opens in a new tab" className="group rounded-xl outline-none transition-transform motion-safe:hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-ring">
        <MetricCard
          title="Deployments"
          value={deploymentHealth.total}
          icon={Activity}
          tone={
            deploymentHealth.total === deploymentHealth.ready
              ? "success"
              : "warning"
          }
          detail={`${deploymentHealth.ready} fully ready`}
        />
        </Link>
        <Link href="/pods" target="_blank" rel="noopener noreferrer" title="Restarts — opens in a new tab" className="group rounded-xl outline-none transition-transform motion-safe:hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-ring">
        <MetricCard
          title="Restarts"
          value={podHealth.restarts}
          icon={Gauge}
          tone={podHealth.restarts > 0 ? "warning" : "success"}
          detail="reported by pod status"
        />
        </Link>
      </div>

      <div className="mt-6 grid items-stretch gap-4 xl:grid-cols-3">
        <ClusterScore
          score={clusterScore}
          healthyPods={podHealth.running}
          totalPods={podHealth.total}
          readyDeployments={deploymentHealth.ready}
          totalDeployments={deploymentHealth.total}
          readyNodes={nodeHealth.ready}
          totalNodes={nodeHealth.total}
        />


          <Card className="h-full min-w-0">
            <CardHeader>
              <CardTitle>Cluster</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ResourceState
                isLoading={cluster.isLoading}
                error={cluster.error}
              />
              {cluster.data ? (
                <div className="grid gap-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Connection</span>
                    <StatusBadge
                      status={cluster.data.connected ? "healthy" : "failed"}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Context</span>
                    <span className="min-w-0 break-all text-right font-medium">{cluster.data.current_context}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">kubectl</span>
                    <Badge variant="outline">{cluster.data.kubectl_version}</Badge>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Server</span>
                    <Badge variant="outline">{cluster.data.server_version}</Badge>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Latency</span>
                    <span className="font-medium">{cluster.data.latency_ms} ms</span>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="h-full min-w-0">
            <CardHeader>
              <CardTitle>Workload Pressure</CardTitle>
            </CardHeader>
            <CardContent>
              <ResourceState
                isLoading={pods.isLoading || deployments.isLoading}
                error={firstError}
              />
              {!firstError && !pods.isLoading && !deployments.isLoading ? (
                <div className="grid gap-3">
                  <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
                    <div className="text-xs text-muted-foreground">Pods</div>
                    <div className="text-xl font-semibold">
                      {podHealth.running}/{podHealth.total}
                    </div>
                  </div>
                  <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
                    <div className="text-xs text-muted-foreground">Deployments</div>
                    <div className="text-xl font-semibold">
                      {deploymentHealth.ready}/{deploymentHealth.total}
                    </div>
                  </div>
                  <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
                    <div className="text-xs text-muted-foreground">Namespaces</div>
                    <div className="flex items-center gap-2 text-xl font-semibold">
                      <Server className="h-5 w-5 text-muted-foreground" />
                      {namespaces.data?.length ?? 0}
                    </div>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </>
    );
}
