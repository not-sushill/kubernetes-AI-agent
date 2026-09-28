"use client";
import { Table } from "@/components/ui/table";

import { formatDateTime, formatAge } from "@/lib/datetime";

import {
  Activity,
  CircleAlert,
  Network,
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
import {
  type ServiceSummary,
  useServiceDetail,
  useServiceEvents,
  useServiceYaml,
  useServices,
} from "@/hooks/use-kubernetes";

export default function ServicesPage() {
  const services = useServices();

  const [selectedService, setSelectedService] =
    useState<ServiceSummary | null>(null);

  const detail = useServiceDetail(selectedService);
  const events = useServiceEvents(selectedService);
  const yaml = useServiceYaml(selectedService);

  const stats = useMemo(() => {
    const rows = services.data ?? [];

    return {
      total: rows.length,
      clusterIP: rows.filter(
        (service) =>
          service.type === "ClusterIP",
      ).length,
      loadBalancer: rows.filter(
        (service) =>
          service.type === "LoadBalancer",
      ).length,
    };
  }, [services.data]);

  return (
    <>
      <PageHeading
        title="Services"
        description="Inspect Kubernetes Services, selectors, ports, endpoints-related events, and configuration."
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle>Cluster Services</CardTitle>

              <button
                type="button"
                onClick={() => services.refetch()}
                disabled={services.isFetching}
                className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
              >
                <RefreshCw
                  className={
                    services.isFetching
                      ? "h-4 w-4 animate-spin"
                      : "h-4 w-4"
                  }
                />
                Refresh
              </button>
            </div>
          </CardHeader>

          <CardContent>
            <ResourceState
              isLoading={services.isLoading}
              error={services.error}
            />

            {!services.error &&
            !services.isLoading ? (
              <div className="space-y-5">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      Total Services
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.total}
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      ClusterIP
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.clusterIP}
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      LoadBalancer
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.loadBalancer}
                    </div>
                  </div>
                </div>

                {services.data?.length ? (
                  <div className="overflow-x-auto rounded-md border border-border">
                    <Table paginate className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/30 text-left">
                          <th className="px-4 py-3 font-medium">
                            Service
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Namespace
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Type
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Cluster IP
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Ports
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Age
                          </th>
                        </tr>
                      </thead>

                      <tbody>
                        {services.data.map(
                          (service) => (
                            <tr
                              key={`${service.namespace}-${service.name}`}
                              onClick={() =>
                                setSelectedService(
                                  service,
                                )
                              }
                              className={`cursor-pointer border-b border-border last:border-0 hover:bg-accent/40 ${
                                selectedService?.namespace ===
                                  service.namespace &&
                                selectedService?.name ===
                                  service.name
                                  ? "bg-accent/50"
                                  : ""
                              }`}
                            >
                              <td className="px-4 py-3 font-medium">
                                {service.name}
                              </td>

                              <td className="px-4 py-3 text-muted-foreground">
                                {service.namespace}
                              </td>

                              <td className="px-4 py-3">
                                <Badge variant="outline">
                                  {service.type}
                                </Badge>
                              </td>

                              <td className="px-4 py-3 text-muted-foreground">
                                {service.cluster_ip}
                              </td>

                              <td className="px-4 py-3">
                                {service.ports
                                  .map(
                                    (port) =>
                                      `${port.port}:${port.target_port}/${port.protocol}`,
                                  )
                                  .join(", ")}
                              </td>

                              <td className="px-4 py-3 text-muted-foreground">
                                {formatAge(service.age)}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </Table>
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                    No Services found.
                  </div>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {selectedService ? (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Network className="h-5 w-5" />
                  Service Details
                </CardTitle>
               
                <div className="text-sm text-muted-foreground">
                  {selectedService.namespace}/
                  {selectedService.name}
                </div>
              </CardHeader>

              <CardContent>
                <ResourceState
                  isLoading={detail.isLoading}
                  error={detail.error}
                />

                {detail.data ? (
                  <div className="space-y-5">
                    <div className="grid gap-4 md:grid-cols-4">
                      <div className="rounded-md border border-border p-4">
                        <div className="text-xs text-muted-foreground">
                          Type
                        </div>
                        <div className="mt-2 font-semibold">
                          {detail.data.type}
                        </div>
                      </div>

                      <div className="rounded-md border border-border p-4">
                        <div className="text-xs text-muted-foreground">
                          Cluster IP
                        </div>
                        <div className="mt-2 font-semibold">
                          {detail.data.cluster_ip}
                        </div>
                      </div>

                      <div className="rounded-md border border-border p-4">
                        <div className="text-xs text-muted-foreground">
                          External IP
                        </div>
                        <div className="mt-2 font-semibold">
                          {detail.data.external_ip ||
                            "None"}
                        </div>
                      </div>

                      <div className="rounded-md border border-border p-4">
                        <div className="text-xs text-muted-foreground">
                          Ports
                        </div>
                        <div className="mt-2 font-semibold">
                          {detail.data.ports.length}
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-6 lg:grid-cols-2">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">
                            Ports
                          </CardTitle>
                        </CardHeader>

                        <CardContent>
                          <div className="space-y-2">
                            {detail.data.ports.map(
                              (port, index) => (
                                <div
                                  key={`${port.port}-${index}`}
                                  className="flex items-center justify-between rounded-md border border-border p-3"
                                >
                                  <span className="font-medium">
                                    {port.name ||
                                      "unnamed"}
                                  </span>

                                  <span className="text-sm text-muted-foreground">
                                    {port.port} →{" "}
                                    {
                                      port.target_port
                                    }{" "}
                                    /{" "}
                                    {port.protocol}
                                  </span>
                                </div>
                              ),
                            )}
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">
                            Selector
                          </CardTitle>
                        </CardHeader>

                        <CardContent>
                          <div className="space-y-2">
                            {Object.entries(
                              detail.data.selector,
                            ).map(
                              ([key, value]) => (
                                <div
                                  key={key}
                                  className="flex justify-between gap-4 rounded-md border border-border p-3 text-sm"
                                >
                                  <span className="text-muted-foreground">
                                    {key}
                                  </span>
                                  <span className="font-medium">
                                    {value}
                                  </span>
                                </div>
                              ),
                            )}

                            {!Object.keys(
                              detail.data.selector,
                            ).length ? (
                              <div className="text-sm text-muted-foreground">
                                No selector configured.
                              </div>
                            ) : null}
                          </div>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="grid gap-6 lg:grid-cols-2">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">
                            Labels
                          </CardTitle>
                        </CardHeader>

                        <CardContent>
                          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-muted/30 p-4 text-xs">
                            {JSON.stringify(
                              detail.data.labels,
                              null,
                              2,
                            )}
                          </pre>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">
                            Annotations
                          </CardTitle>
                        </CardHeader>

                        <CardContent>
                          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-muted/30 p-4 text-xs">
                            {JSON.stringify(
                              detail.data.annotations,
                              null,
                              2,
                            )}
                          </pre>
                        </CardContent>
                      </Card>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Service Events
                </CardTitle>
              </CardHeader>

              <CardContent>
                <ResourceState
                  isLoading={events.isLoading}
                  error={events.error}
                />

                {events.data ? (
                  events.data.events.length ? (
                    <div className="space-y-3">
                      {events.data.events.map(
                        (event, index) => (
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

                              {event.count > 1 ? (
                                <span className="text-xs text-muted-foreground">
                                  × {event.count}
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
                      Service.
                    </div>
                  )
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  Service YAML
                </CardTitle>
              </CardHeader>

              <CardContent>
                <ResourceState
                  isLoading={yaml.isLoading}
                  error={yaml.error}
                />

                {yaml.data ? (
                  <pre className="max-h-[600px] overflow-auto rounded-md bg-muted/30 p-4 text-xs leading-5">
                    {yaml.data.yaml}
                  </pre>
                ) : null}
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="flex min-h-32 flex-col items-center justify-center gap-2 text-center">
              <CircleAlert className="h-5 w-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Select a Service to inspect its details,
                events, selectors, ports, and YAML.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}