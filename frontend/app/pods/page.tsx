// frontend/src/app/pods/page.tsx

"use client";
import { logOptionsForTarget } from "@/lib/log-search";
import { QueueInvestigation } from "@/components/queue-investigation";
import { PodLogViewer } from "@/components/pod-log-viewer";
import type { LogOptions } from "@/hooks/use-kubernetes";
import { ContainerAccess } from "@/components/container-access";
import { formatAge } from "@/lib/datetime";

import Link from "next/link";
import { usePodInvestigationState } from "@/components/pod-investigation-provider";

import {
  Search,
  ShieldAlert,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
} from "lucide-react";
import { InvestigateButton } from "@/components/investigate-button";
import {
  useMemo,
  useState,
} from "react";

import { Button } from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { NamespaceFilter } from "@/components/ui/namespace-filter";
import { PageHeading } from "@/components/ui/page-heading";
import { ResourceState } from "@/components/ui/resource-state";
import { StatusBadge } from "@/components/ui/status-badge";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  DiagnosticIssue,
  PodSummary,
  RootCause,
  useNamespaces,
  usePodLogs,
  usePods,
} from "@/hooks/use-kubernetes";


function getSeverityClass(
  severity?: string,
) {
  switch (
    severity?.toLowerCase()
  ) {
    case "critical":
      return "border-red-500/30 bg-red-500/10 text-red-600";

    case "high":
      return "border-orange-500/30 bg-orange-500/10 text-orange-600";

    case "warning":
    case "medium":
      return "border-yellow-500/30 bg-yellow-500/10 text-yellow-600";

    case "low":
    case "info":
      return "border-blue-500/30 bg-blue-500/10 text-blue-600";

    default:
      return "border-border bg-muted text-muted-foreground";
  }
}


function SeverityBadge({
  severity,
}: {
  severity?: string;
}) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium",
        getSeverityClass(severity),
      ].join(" ")}
    >
      {severity || "unknown"}
    </span>
  );
}


function ConfidenceBadge({
  confidence,
}: {
  confidence: number;
}) {
  const value = Math.max(
    0,
    Math.min(
      100,
      Number(confidence) || 0,
    ),
  );

  return (
    <span className="inline-flex items-center rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium">
      Confidence: {value}%
    </span>
  );
}


function DiagnosticCard({
  issue,
}: {
  issue: DiagnosticIssue;
}) {
  const evidence = Array.isArray(
    issue.evidence,
  )
    ? issue.evidence
    : issue.evidence
      ? [
          String(
            issue.evidence,
          ),
        ]
      : [];

  const possibleCauses =
    Array.isArray(
      issue.possible_causes,
    )
      ? issue.possible_causes
      : [];

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge
                severity={
                  issue.severity
                }
              />

              {issue.category ? (
                <span className="rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                  {issue.category}
                </span>
              ) : null}
            </div>

            <div className="mt-3 font-semibold">
              {issue.title ||
                issue.type ||
                "Diagnostic Issue"}
            </div>

            {issue.description ||
            issue.message ? (
              <p className="mt-2 text-sm text-muted-foreground">
                {issue.description ||
                  issue.message}
              </p>
            ) : null}
          </div>
        </div>

        {issue.container ? (
          <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs">
            <span className="text-muted-foreground">
              Container
            </span>

            <div className="mt-1 font-mono font-medium">
              {issue.container}
            </div>
          </div>
        ) : null}

        {evidence.length > 0 ? (
          <div>
            <div className="mb-2 text-sm font-medium">
              Evidence
            </div>

            <ul className="space-y-2">
              {evidence.map(
                (
                  item,
                  index,
                ) => (
                  <li
                    key={`${item}-${index}`}
                    className="break-all rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground"
                  >
                    {item}
                  </li>
                ),
              )}
            </ul>
          </div>
        ) : null}
        
        {possibleCauses.length >
        0 ? (
          <div>
            <div className="mb-2 text-sm font-medium">
              Possible Causes
            </div>

            <ul className="space-y-2 text-sm text-muted-foreground">
              {possibleCauses.map(
                (
                  cause,
                  index,
                ) => (
                  <li
                    key={`${cause}-${index}`}
                    className="flex gap-2"
                  >
                    <span>
                      •
                    </span>

                    <span>
                      {cause}
                    </span>
                  </li>
                ),
              )}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}


function RootCauseCard({
  rootCause,
}: {
  rootCause: RootCause;
}) {
  const actions =
    rootCause.recommended_actions?.length
      ? rootCause.recommended_actions
      : rootCause.recommended_checks ??
        [];

  return (
    <Card className="border-border">
      <CardContent className="space-y-5 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge
                severity={
                  rootCause.severity
                }
              />

              <ConfidenceBadge
                confidence={
                  Number(rootCause.confidence)
                }
              />

              <span className="rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                {rootCause.category}
              </span>
            </div>

            <h3 className="mt-3 text-base font-semibold">
              {rootCause.title}
            </h3>

            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {rootCause.description ||
                rootCause.summary}
            </p>
          </div>

          <div className="shrink-0">
            {rootCause.severity?.toLowerCase() ===
            "critical" ? (
              <CircleAlert className="h-6 w-6 text-red-500" />
            ) : rootCause.severity?.toLowerCase() ===
              "high" ? (
              <AlertTriangle className="h-6 w-6 text-orange-500" />
            ) : (
              <CheckCircle2 className="h-6 w-6 text-muted-foreground" />
            )}
          </div>
        </div>

        {rootCause.evidence?.length >
        0 ? (
          <div>
            <div className="mb-2 text-sm font-medium">
              Evidence
            </div>

            <div className="space-y-2">
              {rootCause.evidence.map(
                (
                  evidence,
                  index,
                ) => (
                  <div
                    key={`${evidence}-${index}`}
                    className="break-all rounded-md border border-border bg-muted/30 px-3 py-2 font-mono text-xs text-muted-foreground"
                  >
                    {evidence}
                  </div>
                ),
              )}
            </div>
          </div>
        ) : null}

        {actions.length > 0 ? (
          <div>
            <div className="mb-2 text-sm font-medium">
              Recommended Actions
            </div>

            <ol className="space-y-2">
              {actions.map(
                (
                  action,
                  index,
                ) => (
                  <li
                    key={`${action}-${index}`}
                    className="flex gap-3 rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                      {index + 1}
                    </span>

                    <span>
                      {action}
                    </span>
                  </li>
                ),
              )}
            </ol>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}


export default function PodsPage() {
  const [
    namespace,
    setNamespace,
  ] = useState("all");

  const [
    search,
    setSearch,
  ] = useState("");

  const { selectedPod, setSelectedPod, investigationEnabled,
    setInvestigationEnabled, investigation } = usePodInvestigationState();

  const namespaces =
    useNamespaces();

  const pods = usePods(
    namespace === "all"
      ? undefined
      : namespace,
  );

  const logTarget = selectedPod ? `${selectedPod.namespace}/${selectedPod.name}` : "";
  const [logSelection,setLogSelection] = useState<{target:string; options:LogOptions}>({target:"",options:{tail:5000,since:"24h"}});
  const logOptions = logOptionsForTarget(logTarget,logSelection);
  const setLogOptions = (options:LogOptions) => setLogSelection({target:logTarget,options});
  const logs =
    usePodLogs(
      selectedPod,
      logOptions,
    );

  const filteredPods =
    useMemo(() => {
      const rows =
        pods.data ?? [];

      const query =
        search
          .trim()
          .toLowerCase();

      if (!query) {
        return rows;
      }

      return rows.filter(
        (pod) =>
          pod.name
            .toLowerCase()
            .includes(query) ||
          pod.namespace
            .toLowerCase()
            .includes(query) ||
          pod.status
            .toLowerCase()
            .includes(query) ||
          pod.node
            .toLowerCase()
            .includes(query) ||
          pod.pod_ip
            .toLowerCase()
            .includes(query),
      );
    }, [
      pods.data,
      search,
    ]);

  function handleNamespaceChange(
    value: string,
  ) {
    setNamespace(value);
    setSelectedPod(null);
    setInvestigationEnabled(
      false,
    );
  }

  function handleRefresh() {
    void namespaces.refetch();
    void pods.refetch();

    if (selectedPod) {
      void logs.refetch();
    }

    if (
      selectedPod &&
      investigationEnabled
    ) {
      void investigation.refetch();
    }
  }

  function handleViewLogs(
    pod: PodSummary,
  ) {
    const isSelected =
      selectedPod?.namespace ===
        pod.namespace &&
      selectedPod?.name ===
        pod.name;

    if (isSelected) {
      setSelectedPod(null);
      setInvestigationEnabled(
        false,
      );
      return;
    }

    setSelectedPod(pod);
    setInvestigationEnabled(
      false,
    );
  }

  function handleInvestigate(
    pod: PodSummary,
  ) {
    const isSamePod =
      selectedPod?.namespace ===
        pod.namespace &&
      selectedPod?.name ===
        pod.name;

    if (!isSamePod) {
      setSelectedPod(pod);
    }

    setInvestigationEnabled(
      true,
    );
    investigation.run(pod);
  }

  const diagnostics =
    investigation.data
      ?.diagnostics;

  const issues =
    diagnostics?.issues ?? [];

  const rootCauses =
    investigation.data
      ?.root_causes ?? [];

  const rootCauseCount =
    investigation.data
      ?.root_cause_count ??
    rootCauses.length;

  const investigationStatus =
    rootCauses.some(
      (item) =>
        item.severity?.toLowerCase() ===
        "critical",
    )
      ? "Critical issues detected"
      : rootCauses.some(
            (item) =>
              ["critical", "high", "warning", "medium"].includes(
                item.severity?.toLowerCase() ?? "",
              ),
          )
        ? "Issues detected"
        : "No known issues detected";

  return (
    <>
      <PageHeading
        title="Pods"
        description="Inspect Kubernetes pods, collect evidence, diagnose failures, and identify probable root causes."
        actions={
          <NamespaceFilter
            namespaces={
              namespaces.data
            }
            value={namespace}
            onChange={
              handleNamespaceChange
            }
            onRefresh={
              handleRefresh
            }
            isRefreshing={
              namespaces.isFetching ||
              pods.isFetching ||
              logs.isFetching ||
              investigation.isFetching
            }
          />
        }
      />

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <CardTitle>
              Kubernetes Pods
            </CardTitle>

            <div className="relative w-full md:w-80">
              <Search
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />

              <input
                type="search"
                value={search}
                onChange={(
                  event,
                ) =>
                  setSearch(
                    event.target
                      .value,
                  )
                }
                placeholder="Search pods..."
                className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <ResourceState
            isLoading={
              pods.isLoading
            }
            error={
              pods.error
            }
            empty={
              !pods.isLoading &&
              !pods.error &&
              filteredPods.length ===
                0
            }
            emptyLabel="No pods found."
          />
          {selectedPod ? (
            <InvestigateButton
              
              namespace={selectedPod.namespace}
              resourceType="pod"
              resourceName={selectedPod.name}
            />
          ) : null}
          {!pods.isLoading &&
          !pods.error &&
          filteredPods.length >
            0 ? (
            <Table paginate>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    Namespace
                  </TableHead>

                  <TableHead>
                    Name
                  </TableHead>

                  <TableHead>
                    Status
                  </TableHead>

                  <TableHead>
                    Ready
                  </TableHead>

                  <TableHead>
                    Restarts
                  </TableHead>

                  <TableHead>
                    Node
                  </TableHead>

                  <TableHead>
                    Pod IP
                  </TableHead>

                  <TableHead>
                    Age
                  </TableHead>

                  <TableHead className="text-right">
                    Action
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {filteredPods.map(
                  (pod) => {
                    const selected =
                      selectedPod?.namespace ===
                        pod.namespace &&
                      selectedPod?.name ===
                        pod.name;

                    const investigating =
                      selected &&
                      investigationEnabled;

                    return (
                      <TableRow
                        key={`${pod.namespace}/${pod.name}`}
                        data-state={
                          selected
                            ? "selected"
                            : undefined
                        }
                      >
                        <TableCell>
                          {
                            pod.namespace
                          }
                        </TableCell>

                        <TableCell className="font-medium">
                          {pod.name}
                        </TableCell>

                        <TableCell>
                          <StatusBadge
                            status={
                              pod.status
                            }
                          />
                        </TableCell>

                        <TableCell>
                          {pod.ready}
                        </TableCell>

                        <TableCell>
                          <span
                            className={
                              pod.restarts >
                              0
                                ? "font-medium text-warning"
                                : ""
                            }
                          >
                            {
                              pod.restarts
                            }
                          </span>
                        </TableCell>

                        <TableCell>
                          {pod.node ||
                            "-"}
                        </TableCell>

                        <TableCell className="font-mono text-xs">
                          {pod.pod_ip ||
                            "-"}
                        </TableCell>

                        <TableCell>
                          {formatAge(pod.age) ||
                            "-"}
                        </TableCell>

                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              type="button"
                              variant={
                                selected &&
                                !investigationEnabled
                                  ? "secondary"
                                  : "outline"
                              }
                              size="sm"
                              onClick={() =>
                                handleViewLogs(
                                  pod,
                                )
                              }
                            >
                              {selected &&
                              !investigationEnabled
                                ? "Close"
                                : "View Logs"}
                            </Button>

                            <Button
                              type="button"
                              variant={
                                investigating
                                  ? "secondary"
                                  : "outline"
                              }
                              size="sm"
                              onClick={() =>
                                handleInvestigate(
                                  pod,
                                )
                              }
                            >
                              <ShieldAlert className="mr-2 h-4 w-4" />

                              {investigating
                                ? "Investigating"
                                : "Investigate"}
                            </Button>
                            <QueueInvestigation namespace={pod.namespace} resourceType="pod" resourceName={pod.name} />
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  },
                )}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>

      {selectedPod && <ContainerAccess key={`${selectedPod.namespace}/${selectedPod.name}`} namespace={selectedPod.namespace} pod={selectedPod.name} />}

      {selectedPod &&
      !investigationEnabled ? (
        <Card className="mt-6">
          <CardHeader>
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle>
                  Pod Logs
                </CardTitle>
                <InvestigateButton
                  namespace={selectedPod.namespace}
                  resourceType="pod"
                  resourceName={selectedPod.name}
                />
                <p className="mt-1 text-sm text-muted-foreground">
                  {
                    selectedPod.namespace
                  }
                  /
                  {
                    selectedPod.name
                  }
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  void logs.refetch()
                }
                disabled={
                  logs.isFetching
                }
              >
                <RefreshCw className="mr-2 h-4 w-4" />

                {logs.isFetching
                  ? "Refreshing..."
                  : "Refresh Logs"}
              </Button>
            </div>
          </CardHeader>

          <CardContent>
            <PodLogViewer key={`${selectedPod.namespace}/${selectedPod.name}`} options={logOptions} onLoad={value=>{
              if (value.tail===logOptions.tail && value.since===logOptions.since && value.since_time===logOptions.since_time && value.container===logOptions.container && !!value.previous===!!logOptions.previous) void logs.refetch();
              else setLogOptions(value);
            }} data={logs.data} loading={logs.isFetching} error={logs.error} />
          </CardContent>
        </Card>
      ) : null}

      {selectedPod &&
      investigationEnabled ? (
        <div className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle>
                    Pod Investigation
                  </CardTitle>
                  {investigation.data?.id ? (
                    <Link className="text-sm text-primary underline"
                      href={`/investigations/${investigation.data.id}`}>
                      Open saved investigation
                    </Link>
                  ) : null}

                  <p className="mt-1 text-sm text-muted-foreground">
                    {
                      selectedPod.namespace
                    }
                    /
                    {
                      selectedPod.name
                    }
                  </p>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    void investigation.refetch()
                  }
                  disabled={
                    investigation.isFetching
                  }
                >
                  <RefreshCw className="mr-2 h-4 w-4" />

                  {investigation.isFetching
                    ? "Investigating..."
                    : "Run Again"}
                </Button>
              </div>
            </CardHeader>

            <CardContent>
              <ResourceState
                isLoading={
                  investigation.isLoading
                }
                error={
                  investigation.error
                }
                empty={false}
              />

              {!investigation.isLoading &&
              !investigation.error &&
              investigation.data ? (
                <div className="space-y-8">
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Issues Found
                      </div>

                      <div className="mt-2 text-3xl font-bold">
                        {
                          diagnostics?.issue_count ??
                          0
                        }
                      </div>
                    </div>

                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Root Causes
                      </div>

                      <div className="mt-2 text-3xl font-bold">
                        {
                          rootCauseCount
                        }
                      </div>
                    </div>

                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Kubernetes Events
                      </div>

                      <div className="mt-2 text-3xl font-bold">
                        {
                          investigation
                            .data
                            .events
                            .length
                        }
                      </div>
                    </div>

                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">
                        Investigation Status
                      </div>

                      <div className="mt-2 flex items-center gap-2 font-medium">
                        {rootCauses.some(
                          (item) =>
                            item.severity?.toLowerCase() ===
                            "critical",
                        ) ? (
                          <CircleAlert className="h-4 w-4 text-red-500" />
                        ) : rootCauses.length >
                          0 ? (
                          <AlertTriangle className="h-4 w-4 text-orange-500" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}

                        {
                          investigationStatus
                        }
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <div>
                        <h2 className="text-lg font-semibold">
                          Probable Root Causes
                        </h2>

                        <p className="mt-1 text-sm text-muted-foreground">
                          Correlated from Kubernetes events,
                          container logs, pod state, and
                          diagnostic signals.
                        </p>
                      </div>
                    </div>

                    {rootCauses.length ===
                    0 ? (
                      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
                        No probable root causes were identified from the collected evidence.
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {rootCauses.map(
                          (
                            rootCause,
                            index,
                          ) => (
                            <RootCauseCard
                              key={`${rootCause.category}-${rootCause.title}-${index}`}
                              rootCause={
                                rootCause
                              }
                            />
                          ),
                        )}
                      </div>
                    )}
                  </div>

                  <div>
                    <h2 className="mb-3 text-lg font-semibold">
                      Diagnostics
                    </h2>

                    {issues.length ===
                    0 ? (
                      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
                        No known failure patterns were detected from the collected pod evidence.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {issues.map(
                          (
                            issue,
                            index,
                          ) => (
                            <DiagnosticCard
                              key={
                                issue.id ??
                                `${issue.type}-${index}`
                              }
                              issue={
                                issue
                              }
                            />
                          ),
                        )}
                      </div>
                    )}
                  </div>

                  <div>
                    <h2 className="mb-3 text-lg font-semibold">
                      Kubernetes Events
                    </h2>

                    {investigation.data.events
                      .length ===
                    0 ? (
                      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
                        No events were returned for this pod.
                      </div>
                    ) : (
                      <div className="overflow-auto rounded-lg border border-border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>
                                Type
                              </TableHead>

                              <TableHead>
                                Reason
                              </TableHead>

                              <TableHead>
                                Message
                              </TableHead>

                              <TableHead>
                                Count
                              </TableHead>
                            </TableRow>
                          </TableHeader>

                          <TableBody>
                            {investigation.data.events.map(
                              (
                                event,
                                index,
                              ) => (
                                <TableRow
                                  key={`${event.reason}-${index}`}
                                >
                                  <TableCell>
                                    {
                                      event.type
                                    }
                                  </TableCell>

                                  <TableCell className="font-medium">
                                    {
                                      event.reason
                                    }
                                  </TableCell>

                                  <TableCell className="max-w-xl">
                                    {
                                      event.message
                                    }
                                  </TableCell>

                                  <TableCell>
                                    {
                                      event.count
                                    }
                                  </TableCell>
                                </TableRow>
                              ),
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </div>

                  <div>
                    <h2 className="mb-3 text-lg font-semibold">
                      Current Logs
                    </h2>

                    <div className="space-y-4">
                      {Object.entries(
                        investigation.data.logs.current,
                      ).map(
                        ([
                          container,
                          containerLogs,
                        ]) => (
                          <div
                            key={
                              container
                            }
                          >
                            <div className="mb-2 text-sm font-medium">
                              Container:{" "}
                              <span className="font-mono">
                                {
                                  container
                                }
                              </span>
                            </div>

                            <pre className="max-h-[500px] overflow-auto rounded-lg border border-border bg-background p-4 font-mono text-xs leading-5">
                              {containerLogs ||
                                "No logs returned."}
                            </pre>
                          </div>
                        ),
                      )}
                    </div>
                  </div>

                  <div>
                    <h2 className="mb-3 text-lg font-semibold">
                      Previous Logs
                    </h2>

                    <div className="space-y-4">
                      {Object.entries(
                        investigation.data.logs.previous,
                      ).map(
                        ([
                          container,
                          containerLogs,
                        ]) => (
                          <div
                            key={
                              container
                            }
                          >
                            <div className="mb-2 text-sm font-medium">
                              Container:{" "}
                              <span className="font-mono">
                                {
                                  container
                                }
                              </span>
                            </div>

                            <pre className="max-h-[500px] overflow-auto rounded-lg border border-border bg-background p-4 font-mono text-xs leading-5">
                              {containerLogs ||
                                "No previous logs available."}
                            </pre>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </>
  );
}