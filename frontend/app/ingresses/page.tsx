"use client";
import { Table } from "@/components/ui/table";

import { formatDateTime, formatAge } from "@/lib/datetime";

import {
  Globe,
  RefreshCw,
  Route,
  ShieldCheck,
  Waypoints,
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
  type IngressSummary,
  useIngressDetail,
  useIngressEvents,
  useIngressYaml,
  useIngresses,
} from "@/hooks/use-kubernetes";

export default function IngressesPage() {
  const ingresses = useIngresses();

  const [selectedIngress, setSelectedIngress] =
    useState<IngressSummary | null>(null);

  const detail = useIngressDetail(selectedIngress);
  const events = useIngressEvents(selectedIngress);
  const yaml = useIngressYaml(selectedIngress);

  const stats = useMemo(() => {
    const rows = ingresses.data ?? [];

    const hosts = new Set<string>();

    rows.forEach((ingress) => {
      ingress.hosts.forEach((host) => {
        if (host) {
          hosts.add(host);
        }
      });
    });

    return {
      total: rows.length,
      hosts: hosts.size,
      withAddress: rows.filter(
        (ingress) =>
          Boolean(ingress.address) &&
          ingress.address !== "<none>",
      ).length,
      withClass: rows.filter(
        (ingress) =>
          Boolean(ingress.ingress_class),
      ).length,
    };
  }, [ingresses.data]);

  return (
    <>
      <PageHeading
        title="Ingresses"
        description="Inspect Kubernetes Ingress routing, hosts, TLS configuration, events, and YAML."
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle>Cluster Ingresses</CardTitle>

              <button
                type="button"
                onClick={() => ingresses.refetch()}
                disabled={ingresses.isFetching}
                className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw
                  className={
                    ingresses.isFetching
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
              isLoading={ingresses.isLoading}
              error={ingresses.error}
            />

            {!ingresses.error &&
            !ingresses.isLoading ? (
              <div className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      Total Ingresses
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.total}
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      Hosts
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.hosts}
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      With Address
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.withAddress}
                    </div>
                  </div>

                  <div className="rounded-md border border-border p-4">
                    <div className="text-xs text-muted-foreground">
                      Ingress Class
                    </div>
                    <div className="mt-2 text-2xl font-semibold">
                      {stats.withClass}
                    </div>
                  </div>
                </div>

                {ingresses.data?.length ? (
                  <div className="overflow-x-auto rounded-md border border-border">
                    <Table paginate className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/30 text-left">
                          <th className="px-4 py-3 font-medium">
                            Ingress
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Namespace
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Class
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Hosts
                          </th>
                          <th className="px-4 py-3 font-medium">
                            Address
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
                        {ingresses.data.map(
                          (ingress) => {
                            const selected =
                              selectedIngress?.namespace ===
                                ingress.namespace &&
                              selectedIngress?.name ===
                                ingress.name;

                            return (
                              <tr
                                key={`${ingress.namespace}-${ingress.name}`}
                                onClick={() =>
                                  setSelectedIngress(
                                    ingress,
                                  )
                                }
                                className={`cursor-pointer border-b border-border last:border-0 hover:bg-accent/40 ${
                                  selected
                                    ? "bg-accent/50"
                                    : ""
                                }`}
                              >
                                <td className="px-4 py-3 font-medium">
                                  {ingress.name}
                                </td>

                                <td className="px-4 py-3 text-muted-foreground">
                                  {ingress.namespace}
                                </td>

                                <td className="px-4 py-3">
                                  <Badge variant="outline">
                                    {ingress.ingress_class ||
                                      "none"}
                                  </Badge>
                                </td>

                                <td className="max-w-sm px-4 py-3">
                                  <div className="flex flex-wrap gap-1">
                                    {ingress.hosts.length ? (
                                      ingress.hosts.map(
                                        (host) => (
                                          <Badge
                                            key={host}
                                            variant="secondary"
                                          >
                                            {host}
                                          </Badge>
                                        ),
                                      )
                                    ) : (
                                      <span className="text-muted-foreground">
                                        *
                                      </span>
                                    )}
                                  </div>
                                </td>

                                <td className="px-4 py-3 text-muted-foreground">
                                  {ingress.address ||
                                    "None"}
                                </td>

                                <td className="px-4 py-3">
                                  {ingress.ports ||
                                    "-"}
                                </td>

                                <td className="px-4 py-3 text-muted-foreground">
                                  {formatAge(ingress.age)}
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
                    No Ingresses found.
                  </div>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {selectedIngress ? (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Waypoints className="h-5 w-5" />
                  Ingress Details
                </CardTitle>
            
                <div className="text-sm text-muted-foreground">
                  {selectedIngress.namespace}/
                  {selectedIngress.name}
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
                          <Waypoints className="h-4 w-4" />
                          Class
                        </div>

                        <div className="mt-2 font-semibold">
                          {detail.data.ingress_class ||
                            "None"}
                        </div>
                      </div>

                      <div className="rounded-md border border-border p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Globe className="h-4 w-4" />
                          Address
                        </div>

                        <div className="mt-2 break-all font-semibold">
                          {detail.data.address ||
                            "None"}
                        </div>
                      </div>

                      <div className="rounded-md border border-border p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Route className="h-4 w-4" />
                          Routes
                        </div>

                        <div className="mt-2 text-2xl font-semibold">
                          {detail.data.rules.length}
                        </div>
                      </div>

                      <div className="rounded-md border border-border p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <ShieldCheck className="h-4 w-4" />
                          TLS
                        </div>

                        <div className="mt-2 text-2xl font-semibold">
                          {detail.data.tls.length}
                        </div>
                      </div>
                    </div>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">
                          Routing Rules
                        </CardTitle>
                      </CardHeader>

                      <CardContent>
                        {detail.data.rules.length ? (
                          <div className="overflow-x-auto rounded-md border border-border">
                            <Table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-border bg-muted/30 text-left">
                                  <th className="px-4 py-3 font-medium">
                                    Host
                                  </th>
                                  <th className="px-4 py-3 font-medium">
                                    Path
                                  </th>
                                  <th className="px-4 py-3 font-medium">
                                    Service
                                  </th>
                                  <th className="px-4 py-3 font-medium">
                                    Port
                                  </th>
                                </tr>
                              </thead>

                              <tbody>
                                {detail.data.rules.map(
                                  (
                                    rule,
                                    index,
                                  ) => (
                                    <tr
                                      key={`${rule.host}-${rule.path}-${index}`}
                                      className="border-b border-border last:border-0"
                                    >
                                      <td className="px-4 py-3 font-medium">
                                        {rule.host ||
                                          "*"}
                                      </td>

                                      <td className="px-4 py-3">
                                        <Badge variant="outline">
                                          {rule.path ||
                                            "/"}
                                        </Badge>
                                      </td>

                                      <td className="px-4 py-3 font-medium">
                                        {rule.service}
                                      </td>

                                      <td className="px-4 py-3 text-muted-foreground">
                                        {rule.port}
                                      </td>
                                    </tr>
                                  ),
                                )}
                              </tbody>
                            </Table>
                          </div>
                        ) : (
                          <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                            No routing rules found.
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <div className="grid gap-6 lg:grid-cols-2">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">
                            TLS Configuration
                          </CardTitle>
                        </CardHeader>

                        <CardContent>
                          {detail.data.tls.length ? (
                            <div className="space-y-3">
                              {detail.data.tls.map(
                                (
                                  tls,
                                  index,
                                ) => (
                                  <div
                                    key={`${tls.secret_name}-${index}`}
                                    className="rounded-md border border-border p-4"
                                  >
                                    <div className="text-sm font-medium">
                                      Secret
                                    </div>

                                    <div className="mt-1 text-sm text-muted-foreground">
                                      {tls.secret_name ||
                                        "None"}
                                    </div>

                                    <div className="mt-3 text-xs font-medium text-muted-foreground">
                                      Hosts
                                    </div>

                                    <div className="mt-2 flex flex-wrap gap-1">
                                      {tls.hosts.length ? (
                                        tls.hosts.map(
                                          (
                                            host,
                                          ) => (
                                            <Badge
                                              key={
                                                host
                                              }
                                              variant="secondary"
                                            >
                                              {host}
                                            </Badge>
                                          ),
                                        )
                                      ) : (
                                        <span className="text-sm text-muted-foreground">
                                          None
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ),
                              )}
                            </div>
                          ) : (
                            <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                              No TLS configuration found.
                            </div>
                          )}
                        </CardContent>
                      </Card>

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
                    </div>

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
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>
                  Ingress Events
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
                              {formatDateTime(event.last_timestamp)}
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  ) : (
                    <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                      No events reported for this
                      Ingress.
                    </div>
                  )
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>
                  Ingress YAML
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
            <CardContent className="flex min-h-32 items-center justify-center p-8 text-center text-sm text-muted-foreground">
              Select an Ingress to inspect routing,
              TLS, events, annotations, and YAML.
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}