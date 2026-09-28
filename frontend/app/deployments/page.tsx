"use client";
import { useTypedConfirmation } from "@/components/typed-confirmation";
import { formatAge } from "@/lib/datetime";

import {
  CheckCircle2,
  Eye,
  Pencil,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import { formatDateTime } from "@/lib/datetime";
import { InvestigateButton } from "@/components/investigate-button";
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
  DeploymentSummary,
  useApplyDeploymentYaml,
  useDeploymentBackups,
  useDeploymentDetail,
  useDeploymentEvents,
  useDeploymentYaml,
  useDeployments,
  useNamespaces,
  useRestoreDeploymentBackup,
  useValidateDeploymentYaml,
} from "@/hooks/use-kubernetes";

export default function DeploymentsPage() {
  const { confirm, dialog } = useTypedConfirmation();
  const [namespace, setNamespace] = useState("all");

  const [search, setSearch] = useState("");

  const [editableYaml, setEditableYaml] =
    useState("");

  const [isEditingYaml, setIsEditingYaml] =
    useState(false);

  const [validationMessage, setValidationMessage] =
    useState<string | null>(null);

  const [selectedDeployment, setSelectedDeployment] =
    useState<DeploymentSummary | null>(null);

  const namespaces = useNamespaces();

  const deployments = useDeployments(
    namespace === "all"
      ? undefined
      : namespace,
  );

  const detail =
    useDeploymentDetail(
      selectedDeployment,
    );

  const events =
    useDeploymentEvents(
      selectedDeployment,
    );

  const yaml =
    useDeploymentYaml(
      selectedDeployment,
    );

  const backups =
    useDeploymentBackups(
      selectedDeployment,
    );

  const validateYaml =
    useValidateDeploymentYaml();

  const applyYaml =
    useApplyDeploymentYaml();

  const restoreBackup =
    useRestoreDeploymentBackup();

  const filteredDeployments =
    useMemo(() => {
      const rows =
        deployments.data ?? [];

      const query =
        search
          .trim()
          .toLowerCase();

      if (!query) {
        return rows;
      }

      return rows.filter(
        (deployment) =>
          [
            deployment.name,
            deployment.namespace,
          ].some((value) =>
            String(value ?? "")
              .toLowerCase()
              .includes(query),
          ),
      );
    }, [
      deployments.data,
      search,
    ]);

  function handleRefresh() {
    void namespaces.refetch();

    void deployments.refetch();

    if (selectedDeployment) {
      void detail.refetch();

      void events.refetch();

      void yaml.refetch();

      void backups.refetch();
    }
  }

  function handleEditYaml() {
    if (!yaml.data?.yaml) {
      return;
    }

    setEditableYaml(
      yaml.data.yaml,
    );

    setValidationMessage(null);

    setIsEditingYaml(true);
  }

  function handleCancelEdit() {
    setEditableYaml("");

    setValidationMessage(null);

    setIsEditingYaml(false);
  }

  async function handleValidateYaml() {
    if (!selectedDeployment) {
      return;
    }

    setValidationMessage(null);

    try {
      const result =
        await validateYaml.mutateAsync(
          {
            namespace:
              selectedDeployment.namespace,

            deployment:
              selectedDeployment.name,

            yaml: editableYaml,
          },
        );

      setValidationMessage(
        result.message,
      );
    } catch (error) {
      setValidationMessage(
        error instanceof Error
          ? error.message
          : "YAML validation failed.",
      );
    }
  }

  async function handleApplyYaml() {
    if (!selectedDeployment) {
      return;
    }

    const expected = `APPLY ${selectedDeployment.namespace}/${selectedDeployment.name}`;
    const confirmation = await confirm(expected, "Review your edited YAML before applying. This changes the live deployment.");
    if (confirmation !== expected) return;

    try {
      const result =
        await applyYaml.mutateAsync(
          {
            namespace:
              selectedDeployment.namespace,

            deployment:
              selectedDeployment.name,

            yaml: editableYaml,
            confirmation,
          },
        );

      setValidationMessage(
        result.message,
      );

      setIsEditingYaml(false);

      setEditableYaml("");

      void yaml.refetch();

      void detail.refetch();

      void events.refetch();

      void backups.refetch();
    } catch (error) {
      setValidationMessage(
        error instanceof Error
          ? error.message
          : "Failed to apply deployment YAML.",
      );
    }
  }

  async function handleRestoreBackup(
    backupId: string,
  ) {
    if (!selectedDeployment) {
      return;
    }

    const expected = `RESTORE ${selectedDeployment.namespace}/${selectedDeployment.name} ${backupId}`;
    const confirmation = await confirm(expected, "This replaces the live deployment configuration with the selected backup.");
    if (confirmation !== expected) return;

    try {
      const result =
        await restoreBackup.mutateAsync(
          {
            namespace:
              selectedDeployment.namespace,

            deployment:
              selectedDeployment.name,

            backupId,
            confirmation,
          },
        );

      setValidationMessage(
        result.message,
      );

      setIsEditingYaml(false);

      setEditableYaml("");

      void yaml.refetch();

      void detail.refetch();

      void events.refetch();

      void backups.refetch();
    } catch (error) {
      setValidationMessage(
        error instanceof Error
          ? error.message
          : "Failed to restore backup.",
      );
    }
  }

  return (
    <>
      {dialog}
      <PageHeading
        title="Deployments"
        description="Inspect Kubernetes deployments, replica availability and rollout health."
        actions={
          <NamespaceFilter
            namespaces={namespaces.data}
            value={namespace}
            onChange={setNamespace}
            onRefresh={handleRefresh}
            isRefreshing={
              namespaces.isFetching ||
              deployments.isFetching
            }
          />
        }
      />

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <CardTitle>
              Kubernetes Deployments
            </CardTitle>

            <div className="relative w-full md:w-80">
              <Search
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />

              <input
                type="search"
                value={search}
                onChange={(event) =>
                  setSearch(
                    event.target.value,
                  )
                }
                placeholder="Search deployments..."
                className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <ResourceState
            isLoading={
              deployments.isLoading
            }
            error={deployments.error}
            empty={
              !deployments.isLoading &&
              !deployments.error &&
              filteredDeployments.length ===
                0
            }
            emptyLabel="No deployments found."
          />

          {!deployments.isLoading &&
          !deployments.error &&
          filteredDeployments.length >
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
                    Desired
                  </TableHead>

                  <TableHead>
                    Ready
                  </TableHead>

                  <TableHead>
                    Available
                  </TableHead>

                  <TableHead>
                    Updated
                  </TableHead>

                  <TableHead>
                    Status
                  </TableHead>

                  <TableHead>
                    Age
                  </TableHead>

                  <TableHead className="text-right">
                    Actions
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {filteredDeployments.map(
                  (
                    deployment: DeploymentSummary,
                  ) => {
                    const desired =
                      deployment.replicas ??
                      0;

                    const ready =
                      deployment.ready_replicas ??
                      0;

                    const available =
                      deployment.available_replicas ??
                      0;

                    const updated =
                      deployment.updated_replicas ??
                      0;

                    const healthy =
                      desired === ready &&
                      desired ===
                        available;

                    const selected =
                      selectedDeployment?.namespace ===
                        deployment.namespace &&
                      selectedDeployment?.name ===
                        deployment.name;

                    return (
                      <TableRow
                        key={`${deployment.namespace}/${deployment.name}`}
                      >
                        <TableCell>
                          {
                            deployment.namespace
                          }
                        </TableCell>

                        <TableCell className="font-medium">
                          {
                            deployment.name
                          }
                        </TableCell>

                        <TableCell>
                          {desired}
                        </TableCell>

                        <TableCell>
                          {ready}
                        </TableCell>

                        <TableCell>
                          {available}
                        </TableCell>

                        <TableCell>
                          {updated}
                        </TableCell>

                        <TableCell>
                          <StatusBadge
                            status={
                              healthy
                                ? "Healthy"
                                : "Degraded"
                            }
                          />
                        </TableCell>

                        <TableCell>
                          {formatAge(deployment.age) ||
                            "-"}
                        </TableCell>

                        <TableCell className="text-right">
                          <Button
                            type="button"
                            variant={
                              selected
                                ? "secondary"
                                : "outline"
                            }
                            size="sm"
                            onClick={() =>
                              setSelectedDeployment(
                                selected
                                  ? null
                                  : deployment,
                              )
                            }
                          >
                            <Eye
                              className="mr-2 h-4 w-4"
                              aria-hidden="true"
                            />

                            {selected
                              ? "Close"
                              : "View Details"}
                          </Button>
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

      {selectedDeployment ? (
        <Card className="mt-6">
          <CardHeader>
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle>
                  Deployment Details
                </CardTitle>
                <InvestigateButton
                  namespace={selectedDeployment.namespace}
                  resourceType="deployment"
                  resourceName={selectedDeployment.name}
                />
                <p className="mt-1 text-sm text-muted-foreground">
                  {
                    selectedDeployment.namespace
                  }
                  /
                  {
                    selectedDeployment.name
                  }
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  void detail.refetch();
                  void events.refetch();
                  void yaml.refetch();
                  void backups.refetch();
                }}
                disabled={
                  detail.isFetching ||
                  events.isFetching ||
                  yaml.isFetching ||
                  backups.isFetching
                }
              >
                {detail.isFetching ||
                events.isFetching ||
                yaml.isFetching ||
                backups.isFetching
                  ? "Refreshing..."
                  : "Refresh"}
              </Button>
            </div>
          </CardHeader>

          <CardContent>
            <ResourceState
              isLoading={
                detail.isLoading
              }
              error={detail.error}
              empty={
                !detail.isLoading &&
                !detail.error &&
                !detail.data
              }
              emptyLabel="Deployment details not found."
            />

            {detail.data ? (
              <div className="space-y-8">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Namespace
                    </p>

                    <p className="mt-1 font-medium">
                      {detail.data.namespace}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground">
                      Deployment
                    </p>

                    <p className="mt-1 font-medium">
                      {detail.data.name}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground">
                      Strategy
                    </p>

                    <p className="mt-1 font-medium">
                      {detail.data.strategy ||
                        "-"}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-muted-foreground">
                      Ready Replicas
                    </p>

                    <p className="mt-1 font-medium">
                      {detail.data.ready_replicas ??
                        0}
                      {" / "}
                      {detail.data.replicas ??
                        0}
                    </p>
                  </div>
                </div>

                <div className="border-t border-border pt-6">
                  <h3 className="mb-3 text-sm font-semibold">
                    Containers
                  </h3>

                  {detail.data
                    .containers.length >
                  0 ? (
                    <div className="space-y-3">
                      {detail.data.containers.map(
                        (container) => (
                          <div
                            key={
                              container.name
                            }
                            className="rounded-md border border-border p-4"
                          >
                            <p className="font-medium">
                              {
                                container.name
                              }
                            </p>

                            <p className="mt-2 break-all font-mono text-xs text-muted-foreground">
                              {
                                container.image
                              }
                            </p>
                          </div>
                        ),
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No containers found.
                    </p>
                  )}
                </div>

                <div className="border-t border-border pt-6">
                  <h3 className="mb-3 text-sm font-semibold">
                    Conditions
                  </h3>

                  {detail.data.conditions
                    .length > 0 ? (
                    <div className="space-y-3">
                      {detail.data.conditions.map(
                        (
                          condition,
                          index,
                        ) => (
                          <div
                            key={`${condition.type}-${index}`}
                            className="rounded-md border border-border p-4"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-medium">
                                {
                                  condition.type
                                }
                              </span>

                              <StatusBadge
                                status={
                                  condition.status
                                }
                              />
                            </div>

                            {condition.reason ? (
                              <p className="mt-2 text-sm font-medium">
                                {
                                  condition.reason
                                }
                              </p>
                            ) : null}

                            {condition.message ? (
                              <p className="mt-1 text-sm text-muted-foreground">
                                {
                                  condition.message
                                }
                              </p>
                            ) : null}

                            {condition.last_transition_time ? (
                              <p className="mt-2 text-xs text-muted-foreground">
                                Last changed:{" "}
                                {formatDateTime(
                                  condition.last_transition_time,
                                )}
                              </p>
                            ) : null}
                          </div>
                        ),
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No deployment conditions found.
                    </p>
                  )}
                </div>

                <div className="border-t border-border pt-6">
                  <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h3 className="text-sm font-semibold">
                        Deployment YAML
                      </h3>

                      <p className="mt-1 text-xs text-muted-foreground">
                        Review, validate and safely apply deployment configuration changes.
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {!isEditingYaml ? (
                        <>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              void yaml.refetch()
                            }
                            disabled={
                              yaml.isFetching
                            }
                          >
                            {yaml.isFetching
                              ? "Loading..."
                              : "Refresh YAML"}
                          </Button>

                          <Button
                            type="button"
                            size="sm"
                            onClick={
                              handleEditYaml
                            }
                            disabled={
                              yaml.isLoading ||
                              !yaml.data?.yaml
                            }
                          >
                            <Pencil className="mr-2 h-4 w-4" />
                            Edit YAML
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={
                              handleCancelEdit
                            }
                            disabled={
                              validateYaml.isPending ||
                              applyYaml.isPending
                            }
                          >
                            <X className="mr-2 h-4 w-4" />
                            Cancel
                          </Button>

                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              void handleValidateYaml()
                            }
                            disabled={
                              validateYaml.isPending ||
                              applyYaml.isPending
                            }
                          >
                            <CheckCircle2 className="mr-2 h-4 w-4" />

                            {validateYaml.isPending
                              ? "Validating..."
                              : "Validate"}
                          </Button>

                          <Button
                            type="button"
                            size="sm"
                            onClick={() =>
                              void handleApplyYaml()
                            }
                            disabled={
                              validateYaml.isPending ||
                              applyYaml.isPending
                            }
                          >
                            <Save className="mr-2 h-4 w-4" />

                            {applyYaml.isPending
                              ? "Applying..."
                              : "Apply Changes"}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>

                  <ResourceState
                    isLoading={
                      yaml.isLoading
                    }
                    error={yaml.error}
                    empty={
                      Boolean(yaml.data) &&
                      !yaml.data?.yaml
                    }
                    emptyLabel="No YAML returned for this deployment."
                  />

                  {validationMessage ? (
                    <div className="mb-4 rounded-md border border-border bg-muted p-3 text-sm">
                      <div className="flex items-start gap-2">
                        <ShieldCheck
                          className="mt-0.5 h-4 w-4"
                          aria-hidden="true"
                        />

                        <span>
                          {
                            validationMessage
                          }
                        </span>
                      </div>
                    </div>
                  ) : null}

                  {yaml.data?.yaml ? (
                    isEditingYaml ? (
                      <textarea
                        value={
                          editableYaml
                        }
                        onChange={(
                          event,
                        ) =>
                          setEditableYaml(
                            event.target
                              .value,
                          )
                        }
                        spellCheck={false}
                        className="min-h-[600px] w-full resize-y rounded-md border border-border bg-background p-4 font-mono text-xs leading-5 outline-none focus:ring-2 focus:ring-ring"
                      />
                    ) : (
                      <pre className="max-h-[600px] overflow-auto rounded-md border border-border bg-background p-4 font-mono text-xs leading-5">
                        {yaml.data.yaml}
                      </pre>
                    )
                  ) : null}
                </div>

                <div className="border-t border-border pt-6">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold">
                        Deployment Backup History
                      </h3>

                      <p className="mt-1 text-xs text-muted-foreground">
                        Backups are created before YAML changes are applied.
                      </p>
                    </div>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        void backups.refetch()
                      }
                      disabled={
                        backups.isFetching
                      }
                    >
                      {backups.isFetching
                        ? "Loading..."
                        : "Refresh"}
                    </Button>
                  </div>

                  <ResourceState
                    isLoading={
                      backups.isLoading
                    }
                    error={backups.error}
                    empty={
                      !backups.isLoading &&
                      !backups.error &&
                      (backups.data?.length ??
                        0) === 0
                    }
                    emptyLabel="No backups available for this deployment."
                  />

                  {(backups.data?.length ??
                    0) > 0 ? (
                    <div className="space-y-3">
                      {(backups.data ??
                        []).map(
                        (backup) => (
                          <div
                            key={
                              backup.id
                            }
                            className="flex flex-col gap-3 rounded-md border border-border p-4 md:flex-row md:items-center md:justify-between"
                          >
                            <div>
                              <div className="font-mono text-sm font-medium">
                                {
                                  backup.id
                                }
                              </div>

                              <div className="mt-1 text-xs text-muted-foreground">
                                Created:{" "}
                                {formatDateTime(
                                  backup.created_at,
                                )}
                              </div>
                            </div>

                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                void handleRestoreBackup(
                                  backup.id,
                                )
                              }
                              disabled={
                                restoreBackup.isPending
                              }
                            >
                              <RotateCcw className="mr-2 h-4 w-4" />

                              {restoreBackup.isPending
                                ? "Restoring..."
                                : "Restore"}
                            </Button>
                          </div>
                        ),
                      )}
                    </div>
                  ) : null}
                </div>

                <div className="border-t border-border pt-6">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold">
                      Deployment Events
                    </h3>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        void events.refetch()
                      }
                      disabled={
                        events.isFetching
                      }
                    >
                      {events.isFetching
                        ? "Loading..."
                        : "Refresh Events"}
                    </Button>
                  </div>

                  <ResourceState
                    isLoading={
                      events.isLoading
                    }
                    error={events.error}
                    empty={
                      !events.isLoading &&
                      !events.error &&
                      (events.data?.events
                        ?.length ?? 0) === 0
                    }
                    emptyLabel="No events found for this deployment."
                  />

                  {(events.data?.events
                    ?.length ?? 0) > 0 ? (
                    <div className="space-y-3">
                      {(events.data?.events ??
                        []).map(
                        (
                          event,
                          index,
                        ) => (
                          <div
                            key={`${event.reason}-${event.last_timestamp}-${index}`}
                            className="rounded-md border border-border p-3"
                          >
                            <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                              <div>
                                <div className="font-medium">
                                  {event.reason ||
                                    "Event"}
                                </div>

                                <div className="text-sm text-muted-foreground">
                                  {event.message ||
                                    "-"}
                                </div>
                              </div>

                              <StatusBadge
                                status={
                                  event.type ||
                                  "Unknown"
                                }
                              />
                            </div>

                            <div className="mt-2 text-xs text-muted-foreground">
                              Count:{" "}
                              {event.count}{" "}
                              · Last seen:{" "}
                              {formatDateTime(
                                event.last_timestamp,
                              )}
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}