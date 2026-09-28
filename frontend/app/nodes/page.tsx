"use client";
import { Table } from "@/components/ui/table";

import { formatDateTime, formatAge } from "@/lib/datetime";

import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Cpu,
  HardDrive,
  MemoryStick,
  RefreshCw,
  Server,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeading } from "@/components/ui/page-heading";
import { ResourceState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  type NodeCondition,
  type NodeSummary,
  useNodeDetail,
  useNodes,
} from "@/hooks/use-kubernetes";

function conditionIsHealthy(condition: NodeCondition) {
  if (condition.type === "Ready") {
    return condition.status === "True";
  }

  return condition.status !== "True";
}


function healthLabel(score: number | null) {
  if (score === null) return "Unavailable";
  if (score >= 90) {
    return "Healthy";
  }

  if (score >= 70) {
    return "Degraded";
  }

  if (score >= 40) {
    return "Warning";
  }

  return "Critical";
}

function healthVariant(score: number | null) {
  if (score === null) return "secondary" as const;
  if (score >= 90) {
    return "success" as const;
  }

  if (score >= 70) {
    return "secondary" as const;
  }

  return "destructive" as const;
}

function formatMap(
  value: Record<string, string>,
) {
  const entries = Object.entries(value);

  if (!entries.length) {
    return "None";
  }

  return entries
    .map(([key, item]) => `${key}=${item}`)
    .join("\n");
}

export default function NodesPage() {
  const nodes = useNodes();

  const [selectedNode, setSelectedNode] =
    useState<NodeSummary | null>(null);

  const detail = useNodeDetail(
    selectedNode,
  );

  const nodeHealth = useMemo(() => {
    const rows = nodes.data ?? [];

    return {
      total: rows.length,
      ready: rows.filter(
        (node) =>
          node.status.toLowerCase() ===
          "ready",
      ).length,
      unhealthy: rows.filter(
        (node) =>
          node.status.toLowerCase() !==
          "ready",
      ).length,
    };
  }, [nodes.data]);

  return (
    <>
      <PageHeading
        title="Nodes"
        description="Inspect Kubernetes nodes, conditions, capacity, metrics, events, and health."
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle>Cluster Nodes</CardTitle>

              <button
                type="button"
                onClick={() => nodes.refetch()}
                disabled={nodes.isFetching}
                className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw
                  className={`h-4 w-4 ${
                    nodes.isFetching
                      ? "animate-spin"
                      : ""
                  }`}
                />
                Refresh
              </button>
            </div>
          </CardHeader>

          <CardContent>
            <ResourceState
              isLoading={nodes.isLoading}
              error={nodes.error}
            />

            {!nodes.error &&
            !nodes.isLoading ? (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-md border border-border bg-background p-4">
                    <div className="text-xs text-muted-foreground">
                      Total Nodes
                    </div>

                    <div className="mt-2 text-2xl font-semibold">
                      {nodeHealth.total}
                    </div>
                  </div>

                  <div className="rounded-md border border-border bg-background p-4">
                    <div className="text-xs text-muted-foreground">
                      Ready
                    </div>

                    <div className="mt-2 flex items-center gap-2 text-2xl font-semibold">
                      <CheckCircle2 className="h-5 w-5" />
                      {nodeHealth.ready}
                    </div>
                  </div>

                  <div className="rounded-md border border-border bg-background p-4">
                    <div className="text-xs text-muted-foreground">
                      Attention Required
                    </div>

                    <div className="mt-2 flex items-center gap-2 text-2xl font-semibold">
                      <AlertTriangle className="h-5 w-5" />
                      {nodeHealth.unhealthy}
                    </div>
                  </div>
                </div>

                {nodes.data?.length ? (
                  <div className="overflow-x-auto rounded-md border border-border">
                    <Table paginate className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/30 text-left">
                          <th className="px-4 py-3 font-medium">
                            Node
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Status
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Role
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Version
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Age
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {nodes.data.map(
                          (node) => {
                            const selected =
                              selectedNode?.name ===
                              node.name;

                            return (
                              <tr
                                key={node.name}
                                onClick={() =>
                                  setSelectedNode(
                                    node,
                                  )
                                }
                                className={`cursor-pointer border-b border-border last:border-0 hover:bg-accent/40 ${
                                  selected
                                    ? "bg-accent/50"
                                    : ""
                                }`}
                              >
                                <td className="px-4 py-3 font-medium">
                                  {node.name}
                                </td>

                                <td className="px-4 py-3">
                                  <StatusBadge
                                    status={
                                      node.status
                                    }
                                  />
                                </td>

                                <td className="px-4 py-3 text-muted-foreground">
                                  {node.roles ||
                                    "worker"}
                                </td>

                                <td className="px-4 py-3 text-muted-foreground">
                                  {node.version}
                                </td>

                                <td className="px-4 py-3 text-muted-foreground">
                                  {formatAge(node.age)}
                                </td>
                              </tr>
                            );
                          },
                        )}
                      </tbody>
                    </Table>
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                    No Kubernetes nodes found.
                  </div>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {selectedNode ? (
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle>
                    Node Investigation
                  </CardTitle>
                 
                  <div className="mt-1 text-sm text-muted-foreground">
                    {selectedNode.name}
                  </div>
                </div>

                {detail.data ? (
                  <Badge
                    variant={healthVariant(
                      detail.data.health_score,
                    )}
                  >
                    {healthLabel(
                      detail.data.health_score,
                    )}{" "}
                    ·{" "}
                    {detail.data.health_score === null ? "Not assessed" : detail.data.health_score + "/100"}
                  </Badge>
                ) : null}
              </div>
            </CardHeader>

            <CardContent>
              <ResourceState
                isLoading={detail.isLoading}
                error={detail.error}
              />

              {detail.data ? (
                <div className="space-y-6">
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-md border border-border p-4">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Server className="h-4 w-4" />
                        Status
                      </div>

                      <div className="mt-2">
                        <StatusBadge
                          status={
                            detail.data.status
                          }
                         
                  
                        />
                      </div>
                    </div>

                    <div className="rounded-md border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Roles
                      </div>

                      <div className="mt-2 font-semibold">
                        {detail.data.roles ||
                          "worker"}
                      </div>
                    </div>

                    <div className="rounded-md border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Scheduling
                      </div>

                      <div className="mt-2 flex items-center gap-2 font-semibold">
                        {detail.data.unschedulable ? (
                          <>
                            <Circle className="h-4 w-4" />
                            Unschedulable
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="h-4 w-4" />
                            Schedulable
                          </>
                        )}
                      </div>
                    </div>

                    <div className="rounded-md border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Health Score
                      </div>

                      <div className="mt-2 text-2xl font-semibold">
                        {detail.data.health_score ?? "Unavailable"}
                        <span className="text-sm font-normal text-muted-foreground">
                          {detail.data.health_score === null ? "" : "/100"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-3">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Cpu className="h-4 w-4" />
                          CPU
                        </CardTitle>
                      </CardHeader>

                      <CardContent>
                        <div className="text-lg font-semibold">
                          {detail.data.metrics.available
                            ? detail.data.metrics.cpu ||
                              "Unavailable"
                            : "Metrics unavailable"}
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <MemoryStick className="h-4 w-4" />
                          Memory
                        </CardTitle>
                      </CardHeader>

                      <CardContent>
                        <div className="text-lg font-semibold">
                          {detail.data.metrics.available
                            ? detail.data.metrics.memory ||
                              "Unavailable"
                            : "Metrics unavailable"}
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <HardDrive className="h-4 w-4" />
                          Conditions
                        </CardTitle>
                      </CardHeader>

                      <CardContent>
                        <div className="text-lg font-semibold">
                          {
                            detail.data.conditions.filter(
                              conditionIsHealthy,
                            ).length
                          }
                          /
                          {
                            detail.data.conditions
                              .length
                          }{" "}
                          healthy
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Card>
                    <CardHeader>
                      <CardTitle>Node Conditions</CardTitle>
                    </CardHeader>

                    <CardContent>
                      <div className="overflow-x-auto rounded-md border border-border">
                        <Table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/30 text-left">
                              <th className="px-4 py-3 font-medium">
                                Condition
                              </th>
                              <th className="px-4 py-3 font-medium">
                                Status
                              </th>
                              <th className="px-4 py-3 font-medium">
                                Reason
                              </th>
                              <th className="px-4 py-3 font-medium">
                                Message
                              </th>
                            </tr>
                          </thead>

                          <tbody>
                            {detail.data.conditions.map(
                              (
                                condition,
                                index,
                              ) => {
                                const healthy =
                                  conditionIsHealthy(
                                    condition,
                                  );

                                return (
                                  <tr
                                    key={`${condition.type}-${index}`}
                                    className="border-b border-border last:border-0"
                                  >
                                    <td className="px-4 py-3 font-medium">
                                      {condition.type}
                                    </td>

                                    <td className="px-4 py-3">
                                      <Badge
                                        variant={
                                          healthy
                                            ? "success"
                                            : "destructive"
                                        }
                                      >
                                        {condition.status}
                                      </Badge>
                                    </td>

                                    <td className="px-4 py-3 text-muted-foreground">
                                      {condition.reason ||
                                        "-"}
                                    </td>

                                    <td className="max-w-xl px-4 py-3 text-muted-foreground">
                                      {condition.message ||
                                        "-"}
                                    </td>
                                  </tr>
                                );
                              },
                            )}
                          </tbody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>

                  <div className="grid gap-6 lg:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle>
                          Node Information
                        </CardTitle>
                      </CardHeader>

                      <CardContent>
                        <div className="space-y-3 text-sm">
                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              Version
                            </span>
                            <span className="font-medium">
                              {detail.data.version}
                            </span>
                          </div>

                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              Internal IP
                            </span>
                            <span className="font-medium">
                              {detail.data.internal_ip}
                            </span>
                          </div>

                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              OS
                            </span>
                            <span className="text-right font-medium">
                              {detail.data.os_image}
                            </span>
                          </div>

                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              Kernel
                            </span>
                            <span className="text-right font-medium">
                              {detail.data.kernel_version}
                            </span>
                          </div>

                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              Runtime
                            </span>
                            <span className="text-right font-medium">
                              {
                                detail.data
                                  .container_runtime
                              }
                            </span>
                          </div>

                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              Provider ID
                            </span>
                            <span className="break-all text-right font-medium">
                              {
                                detail.data
                                  .provider_id
                              }
                            </span>
                          </div>

                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              Pod CIDR
                            </span>
                            <span className="font-medium">
                              {detail.data.pod_cidr}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle>Capacity</CardTitle>
                      </CardHeader>

                      <CardContent>
                        <div className="grid gap-4 sm:grid-cols-2">
                          <div>
                            <div className="mb-2 text-xs font-medium text-muted-foreground">
                              Capacity
                            </div>

                            <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded-md bg-muted/30 p-3 text-xs">
                              {formatMap(
                                detail.data.capacity,
                              )}
                            </pre>
                          </div>

                          <div>
                            <div className="mb-2 text-xs font-medium text-muted-foreground">
                              Allocatable
                            </div>

                            <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded-md bg-muted/30 p-3 text-xs">
                              {formatMap(
                                detail.data.allocatable,
                              )}
                            </pre>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Card>
                    <CardHeader>
                      <CardTitle>
                        Node Events
                      </CardTitle>
                    </CardHeader>

                    <CardContent>
                      {detail.data.events.length ? (
                        <div className="space-y-3">
                          {detail.data.events.map(
                            (
                              event,
                              index,
                            ) => (
                              <div
                                key={`${event.reason}-${index}`}
                                className="rounded-md border border-border p-4"
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge
                                    variant={
                                      event.type ===
                                      "Warning"
                                        ? "destructive"
                                        : "secondary"
                                    }
                                  >
                                    {event.type}
                                  </Badge>

                                  <span className="font-medium">
                                    {event.reason ||
                                      "Event"}
                                  </span>

                                  {event.count >
                                  1 ? (
                                    <span className="text-xs text-muted-foreground">
                                      ×{" "}
                                      {
                                        event.count
                                      }
                                    </span>
                                  ) : null}
                                </div>

                                <p className="mt-2 text-sm text-muted-foreground">
                                  {event.message}
                                </p>

                                <div className="mt-2 text-xs text-muted-foreground">
                                  Last seen:{" "}
                                  {
                                    formatDateTime(event.last_timestamp)
                                  }
                                </div>
                              </div>
                            ),
                          )}
                        </div>
                      ) : (
                        <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                          No events reported for this
                          node.
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>
                        Node YAML
                      </CardTitle>
                    </CardHeader>

                    <CardContent>
                      <pre className="max-h-[500px] overflow-auto rounded-md bg-muted/30 p-4 text-xs leading-5">
                        {detail.data.yaml}
                      </pre>
                    </CardContent>
                  </Card>
                </div>
              ) : null}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              Select a node to inspect its health,
              conditions, resources, events, and
              configuration.
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}