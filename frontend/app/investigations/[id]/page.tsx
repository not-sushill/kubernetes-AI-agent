"use client";
import { formatDateTime } from "@/lib/datetime";

import Link from "next/link";
import { AiFixAssistant } from "@/components/ai-fix-assistant";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Clock3,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { useParams } from "next/navigation";

import { Button } from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { PageHeading } from "@/components/ui/page-heading";

import { ResourceState } from "@/components/ui/resource-state";

import { StatusBadge } from "@/components/ui/status-badge";

import { useInvestigation } from "@/hooks/use-kubernetes";

const formatDate = formatDateTime;

function getSectionData(section: {
  status?: string;
  data?: unknown;
  error?: string | null;
}) {
  if (
    section.data === null ||
    section.data === undefined
  ) {
    return null;
  }

  return section.data;
}

function SectionStatus({
  status,
}: {
  status: string;
}) {
  const normalized = status.toLowerCase();

  if (normalized === "collected") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600">
        <CheckCircle2 className="h-4 w-4" />
        Collected
      </span>
    );
  }

  if (normalized === "failed") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-red-600">
        <XCircle className="h-4 w-4" />
        Failed
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <Clock3 className="h-4 w-4" />
      Skipped
    </span>
  );
}

function JsonBlock({
  value,
}: {
  value: unknown;
}) {
  if (
    value === null ||
    value === undefined
  ) {
    return (
      <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
        No data available.
      </div>
    );
  }

  if (typeof value === "string") {
    return (
      <pre className="max-h-[500px] overflow-auto rounded-md border border-border bg-background p-4 font-mono text-xs leading-5">
        {value}
      </pre>
    );
  }

  return (
    <pre className="max-h-[500px] overflow-auto rounded-md border border-border bg-background p-4 font-mono text-xs leading-5">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function EvidenceSection({
  title,
  section,
}: {
  title: string;
  section: {
    status: string;
    data?: unknown;
    error?: string | null;
  };
}) {
  const sectionData = getSectionData(section);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-base">
            {title}
          </CardTitle>

          <SectionStatus
            status={section.status}
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {section.error ? (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
            {section.error}
          </div>
        ) : null}

        {sectionData !== null ? (
          <JsonBlock value={sectionData} />
        ) : !section.error ? (
          <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
            No data collected.
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function InvestigationDetailPage() {
  const params = useParams<{
    id: string;
  }>();

  const investigationId =
    typeof params?.id === "string"
      ? params.id
      : null;

  const investigation =
    useInvestigation(investigationId);

  const data = investigation.data;

  const status = data?.status ?? "";
  const statusLower = status.toLowerCase();

  return (
    <>
      {investigationId && <Link className="mb-3 inline-block text-sm text-primary" href={`/operations?investigation=${investigationId}`}>Timeline · Changes · Verification →</Link>}
      <PageHeading
        title="Investigation"
        description="View the complete evidence and analysis collected during a Kubernetes investigation."
        actions={
          <div className="flex gap-2">
            <Button
              asChild
              variant="outline"
              size="sm"
            >
              <Link href="/investigations">
                <ArrowLeft className="mr-2 h-4 w-4" />
                History
              </Link>
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                void investigation.refetch()
              }
              disabled={investigation.isFetching}
            >
              <RefreshCw className="mr-2 h-4 w-4" />

              {investigation.isFetching
                ? "Refreshing..."
                : "Refresh"}
            </Button>
          </div>
        }
      />

      <ResourceState
        isLoading={investigation.isLoading}
        error={investigation.error}
        empty={
          !investigation.isLoading &&
          !investigation.error &&
          !data
        }
        emptyLabel="Investigation not found."
      />

      {!investigation.isLoading &&
      !investigation.error &&
      data ? (
        <div className="space-y-6">
          <AiFixAssistant key={data.id} investigationId={data.id} defaultDeployment={data.target.resource_type === "deployment" ? data.target.resource_name : ""} />
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <CardTitle>
                    Investigation Summary
                  </CardTitle>

                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {data.id}
                  </p>
                </div>

                <StatusBadge status={data.status} />
              </div>
            </CardHeader>

            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground">
                    Namespace
                  </div>

                  <div className="mt-2 font-medium">
                    {data.target.namespace}
                  </div>
                </div>

                <div className="rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground">
                    Resource Type
                  </div>

                  <div className="mt-2 font-medium">
                    {data.target.resource_type}
                  </div>
                </div>

                <div className="rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground">
                    Resource Name
                  </div>

                  <div className="mt-2 break-all font-medium">
                    {data.target.resource_name}
                  </div>
                </div>

                <div className="rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground">
                    Created
                  </div>

                  <div className="mt-2 text-sm">
                    {formatDate(data.created_at)}
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-lg border border-border p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  {statusLower === "completed" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : statusLower === "failed" ? (
                    <CircleAlert className="h-4 w-4 text-red-600" />
                  ) : (
                    <Clock3 className="h-4 w-4 text-muted-foreground" />
                  )}

                  Investigation status: {data.status}
                </div>

                <div className="mt-1 text-xs text-muted-foreground">
                  Last updated {formatDate(data.updated_at)}
                </div>
              </div>
            </CardContent>
          </Card>

          <div>
            <h2 className="mb-3 text-lg font-semibold">
              Investigation Analysis
            </h2>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <CardTitle className="text-base">
                      Summary
                    </CardTitle>

                    {data.analysis?.ai ? (
                      <StatusBadge
                        status={
                          data.analysis.ai.severity
                        }
                      />
                    ) : null}
                  </div>
                </CardHeader>

                <CardContent>
                  <p className="text-sm leading-6">
                    {data.analysis?.ai?.summary ??
                      "No analysis available."}
                  </p>

                  {data.analysis?.ai ? (
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      <div className="rounded-lg border border-border p-4">
                        <div className="text-xs text-muted-foreground">
                          Severity
                        </div>

                        <div className="mt-1 font-medium">
                          {
                            data.analysis.ai
                              .severity
                          }
                        </div>
                      </div>

                      <div className="rounded-lg border border-border p-4">
                        <div className="text-xs text-muted-foreground">
                          Confidence
                        </div>

                        <div className="mt-1 font-medium">
                          {Math.round(
                            data.analysis.ai
                              .confidence,
                          )}
                          %
                        </div>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              {data.analysis?.ai?.root_causes &&
              data.analysis.ai.root_causes.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Probable Root Causes
                    </CardTitle>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {data.analysis.ai.root_causes.map(
                      (cause, index: number) => (
                        <div
                          key={`${cause.title}-${index}`}
                          className="rounded-lg border border-border p-4"
                        >
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <div className="font-medium">
                                {cause.title}
                              </div>

                              <p className="mt-1 text-sm text-muted-foreground">
                                {cause.explanation}
                              </p>
                            </div>

                            <div className="shrink-0 text-xs text-muted-foreground">
                              {Math.round(
                                cause.confidence,
                              )}
                              % confidence
                            </div>
                          </div>

                          {cause.evidence &&
                          cause.evidence.length > 0 ? (
                            <div className="mt-3">
                              <div className="mb-1 text-xs font-medium">
                                Evidence
                              </div>

                              <ul className="space-y-1 text-xs text-muted-foreground">
                                {cause.evidence.map(
                                  (
                                    item: string,
                                    evidenceIndex: number,
                                  ) => (
                                    <li
                                      key={`${item}-${evidenceIndex}`}
                                    >
                                      {item}
                                    </li>
                                  ),
                                )}
                              </ul>
                            </div>
                          ) : null}
                        </div>
                      ),
                    )}
                  </CardContent>
                </Card>
              ) : null}

              {data.analysis?.ai?.recommendations &&
              data.analysis.ai.recommendations.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Recommended Actions
                    </CardTitle>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {data.analysis.ai.recommendations.map(
                      (
                        recommendation,
                        index: number,
                      ) => (
                        <div
                          key={`${recommendation.action}-${index}`}
                          className="rounded-lg border border-border p-4"
                        >
                          <div className="font-medium">
                            {recommendation.action}
                          </div>

                          <div className="mt-1 text-sm text-muted-foreground">
                            {recommendation.reason}
                          </div>

                          <div className="mt-2 text-xs text-muted-foreground">
                            Risk:{" "}
                            {recommendation.risk}
                          </div>

                          {recommendation.commands &&
                          recommendation.commands.length > 0 ? (
                            <pre className="mt-3 overflow-auto rounded-md border border-border bg-muted/20 p-3 text-xs">
                              {recommendation.commands.join(
                                "\n",
                              )}
                            </pre>
                          ) : null}
                        </div>
                      ),
                    )}
                  </CardContent>
                </Card>
              ) : null}

              {data.analysis?.ai?.limitations &&
              data.analysis.ai.limitations.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Analysis Limitations
                    </CardTitle>
                  </CardHeader>

                  <CardContent>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      {data.analysis.ai.limitations.map(
                        (
                          item: string,
                          index: number,
                        ) => (
                          <li
                            key={`${item}-${index}`}
                          >
                            {item}
                          </li>
                        ),
                      )}
                    </ul>
                  </CardContent>
                </Card>
              ) : null}
            </div>
          </div>

<div>
  <h2 className="mb-3 text-lg font-semibold">
    Investigation Analysis
  </h2>

  <div className="space-y-4">

    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Deterministic Diagnostics
        </CardTitle>
      </CardHeader>

      <CardContent>
        {data.analysis?.diagnostics &&
        data.analysis.diagnostics.length > 0 ? (
          <div className="space-y-3">
            {data.analysis.diagnostics.map(
              (
                issue,
                index: number,
              ) => (
                <div
                  key={`diagnostic-${index}`}
                  className="rounded-lg border border-border p-4"
                >
                  <div className="font-medium">
                    {String(
                      issue.title ??
                      issue.message ??
                      issue.name ??
                      issue.code ??
                      "Detected issue",
                    )}
                  </div>

                  {issue.description ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {String(
                        issue.description,
                      )}
                    </p>
                  ) : null}

                  {issue.severity ? (
                    <div className="mt-2 text-xs">
                      Severity:{" "}
                      {String(
                        issue.severity,
                      )}
                    </div>
                  ) : null}

                  {Array.isArray(
                    issue.evidence,
                  ) ? (
                    <div className="mt-3">
                      <div className="text-xs font-medium">
                        Evidence
                      </div>

                      <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                        {issue.evidence.map(
                          (
                            evidenceItem,
                            evidenceIndex,
                          ) => (
                            <li
                              key={`diagnostic-evidence-${index}-${evidenceIndex}`}
                            >
                              {String(
                                evidenceItem,
                              )}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ),
            )}
          </div>
        ) : (
          <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
            No deterministic issues detected.
          </div>
        )}
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Probable Root Causes
        </CardTitle>
      </CardHeader>

      <CardContent>
        {data.analysis?.root_causes &&
        data.analysis.root_causes.length > 0 ? (
          <div className="space-y-3">
            {data.analysis.root_causes.map(
              (
                cause,
                index: number,
              ) => (
                <div
                  key={`root-cause-${index}`}
                  className="rounded-lg border border-border p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="font-medium">
                        {String(
                          cause.title ??
                          cause.reason ??
                          cause.name ??
                          "Probable root cause",
                        )}
                      </div>

                      {cause.explanation ||
                      cause.description ? (
                        <p className="mt-1 text-sm text-muted-foreground">
                          {String(
                            cause.explanation ??
                            cause.description,
                          )}
                        </p>
                      ) : null}
                    </div>

                    {cause.confidence !==
                    undefined ? (
                      <div className="shrink-0 text-xs text-muted-foreground">
                        {Math.round(
                          Number(
                            cause.confidence,
                          ),
                        )}
                        % confidence
                      </div>
                    ) : null}
                  </div>

                  {Array.isArray(
                    cause.evidence,
                  ) &&
                  cause.evidence.length > 0 ? (
                    <div className="mt-3">
                      <div className="text-xs font-medium">
                        Evidence
                      </div>

                      <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                        {cause.evidence.map(
                          (
                            evidenceItem,
                            evidenceIndex,
                          ) => (
                            <li
                              key={`root-evidence-${index}-${evidenceIndex}`}
                            >
                              {String(
                                evidenceItem,
                              )}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ),
            )}
          </div>
        ) : (
          <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
            No probable root causes detected.
          </div>
        )}
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          AI Diagnosis
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {data.analysis?.ai ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-border p-4">
                <div className="text-xs text-muted-foreground">
                  Severity
                </div>

                <div className="mt-1 font-medium">
                  {
                    data.analysis.ai
                      .severity
                  }
                </div>
              </div>

              <div className="rounded-lg border border-border p-4">
                <div className="text-xs text-muted-foreground">
                  Confidence
                </div>

                <div className="mt-1 font-medium">
                  {Math.round(
                    data.analysis.ai
                      .confidence,
                  )}
                  %
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-border p-4">
              <div className="text-sm leading-6">
                {
                  data.analysis.ai
                    .summary
                }
              </div>
            </div>
          </>
        ) : (
          <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
            AI diagnosis is unavailable.
          </div>
        )}
      </CardContent>
    </Card>

  </div>
</div>
          <div>
            <h2 className="mb-3 text-lg font-semibold">
              Collected Evidence
            </h2>

            <div className="grid gap-4">
              <EvidenceSection
                title="Namespace"
                section={data.evidence.namespace}
              />

              <EvidenceSection
                title="Pod"
                section={data.evidence.pod}
              />

              <EvidenceSection
                title="Deployment"
                section={data.evidence.deployment}
              />

              <EvidenceSection
                title="ReplicaSet"
                section={data.evidence.replicaset}
              />

              <EvidenceSection
                title="Node"
                section={data.evidence.node}
              />

              <EvidenceSection
                title="Kubernetes Events"
                section={data.evidence.events}
              />

              <EvidenceSection
                title="Logs"
                section={data.evidence.logs}
              />

              <EvidenceSection
                title="Services"
                section={data.evidence.services}
              />

              <EvidenceSection
                title="Persistent Volume Claims"
                section={data.evidence.pvc}
              />

              <EvidenceSection
                title="Metrics"
                section={data.evidence.metrics}
              />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}