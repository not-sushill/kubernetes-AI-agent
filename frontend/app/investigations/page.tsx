// ============================================================
// 7. frontend/app/investigations/page.tsx
// ============================================================

"use client";
import { Table } from "@/components/ui/table";

import { formatDateTime } from "@/lib/datetime";

import Link from "next/link";
import { useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Search,
} from "lucide-react";

import { Button } from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";

import { PageHeading } from "@/components/ui/page-heading";

import { ResourceState } from "@/components/ui/resource-state";

import { StatusBadge } from "@/components/ui/status-badge";

import { useInvestigations } from "@/hooks/use-kubernetes";

const formatDate = formatDateTime;

export default function InvestigationsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [namespace, setNamespace] = useState("");
  const [status, setStatus] = useState("");
  const [resourceType, setResourceType] = useState("");

  const [pageSize, setPageSize] = useState(10);

  const investigations = useInvestigations({
    page,
    page_size: pageSize,
    search: search.trim() || undefined,
    namespace: namespace.trim() || undefined,
    status: status || undefined,
    resource_type: resourceType || undefined,
  });

  const data = investigations.data;
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.pages ?? 0;
  const currentPage = data?.page ?? page;

  return (
    <>
      <PageHeading
        title="Investigation History"
        description="Review previous Kubernetes investigations. Click column headings to sort the current page; filters search all saved records."
        actions={
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void investigations.refetch()}
            disabled={investigations.isFetching}
          >
            <RefreshCw className="mr-2 h-4 w-4" />

            {investigations.isFetching
              ? "Refreshing..."
              : "Refresh"}
          </Button>
        }
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Filters
            </CardTitle>
          </CardHeader>

          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <label
                  htmlFor="investigation-search"
                  className="text-sm font-medium"
                >
                  Search
                </label>

                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                  <Input
                    id="investigation-search"
                    value={search}
                    onChange={(event) => {
                      setSearch(event.target.value);
                      setPage(1);
                    }}
                    placeholder="Search resource..."
                    className="pl-9"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="investigation-namespace"
                  className="text-sm font-medium"
                >
                  Namespace
                </label>

                <Input
                  id="investigation-namespace"
                  value={namespace}
                  onChange={(event) => {
                    setNamespace(event.target.value);
                    setPage(1);
                  }}
                  placeholder="default"
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="investigation-status"
                  className="text-sm font-medium"
                >
                  Status
                </label>

                <select
                  id="investigation-status"
                  value={status}
                  onChange={(event) => {
                    setStatus(event.target.value);
                    setPage(1);
                  }}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">All statuses</option>
                  <option value="RUNNING">RUNNING</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="PARTIAL">PARTIAL</option>
                  <option value="FAILED">FAILED</option>
                </select>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="investigation-resource-type"
                  className="text-sm font-medium"
                >
                  Resource Type
                </label>

                <select
                  id="investigation-resource-type"
                  value={resourceType}
                  onChange={(event) => {
                    setResourceType(event.target.value);
                    setPage(1);
                  }}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">All resource types</option>
                  <option value="namespace">Namespace</option>
                  <option value="pod">Pod</option>
                  <option value="deployment">Deployment</option>
                </select>
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearch("");
                  setNamespace("");
                  setStatus("");
                  setResourceType("");
                  setPage(1);
                }}
              >
                Clear filters
              </Button>
            </div>
          </CardContent>
        </Card>

        <ResourceState
          isLoading={investigations.isLoading}
          error={investigations.error}
          empty={
            !investigations.isLoading &&
            !investigations.error &&
            items.length === 0
          }
          emptyLabel="No investigations found."
        />

        {!investigations.isLoading &&
          !investigations.error &&
          items.length > 0 ? (
          <>
            <Card>
              <CardHeader>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle className="text-base">
                    Investigations
                  </CardTitle>

                  <div className="text-sm text-muted-foreground">
                    {total} investigation
                    {total === 1 ? "" : "s"}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/30">
                        <th className="px-4 py-3 text-left font-medium">
                          Resource
                        </th>

                        <th className="px-4 py-3 text-left font-medium">
                          Namespace
                        </th>

                        <th className="px-4 py-3 text-left font-medium">
                          Cluster
                        </th>

                        <th className="px-4 py-3 text-left font-medium">
                          Status
                        </th>

                        <th className="px-4 py-3 text-left font-medium">
                          Created
                        </th>

                        <th className="px-4 py-3 text-right font-medium">
                          Action
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {items.map((item) => (
                        <tr
                          key={item.id}
                          className="border-b border-border last:border-0 hover:bg-muted/20"
                        >
                          <td className="px-4 py-4 align-top">
                            <div className="flex flex-col gap-1">
                              <Link
                                href={`/investigations/${encodeURIComponent(
                                  item.id,
                                )}`}
                                className="font-medium text-primary hover:underline"
                              >
                                {item.resource_name}
                              </Link>

                              <span className="text-xs text-muted-foreground">
                                {item.resource_type}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-4 align-top">
                            <span className="font-mono text-xs">
                              {item.namespace}
                            </span>
                          </td>

                          <td className="px-4 py-4 align-top">
                            {item.cluster}
                          </td>

                          <td className="px-4 py-4 align-top">
                            <StatusBadge status={item.status} />
                          </td>

                          <td className="px-4 py-4 align-top">
                            {formatDate(item.created_at)}
                          </td>

                          <td className="px-4 py-4 text-right align-top">
                            <Button
                              asChild
                              variant="outline"
                              size="sm"
                            >
                              <Link
                                href={`/investigations/${encodeURIComponent(
                                  item.id,
                                )}`}
                              >
                                View
                              </Link>
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-muted-foreground">
                Page {currentPage}
                {totalPages > 0
                  ? ` of ${totalPages}`
                  : ""}
              </div>

              <div className="flex items-center gap-2">
                <label className="text-sm">Rows per page <select className="rounded-md border bg-background p-2" value={pageSize} onChange={e => {setPageSize(Number(e.target.value)); setPage(1);}}><option value={5}>5</option><option value={10}>10</option></select></label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() =>
                    setPage((value) =>
                      Math.max(1, value - 1),
                    )
                  }
                >
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Previous
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={
                    totalPages === 0 ||
                    currentPage >= totalPages
                  }
                  onClick={() =>
                    setPage((value) =>
                      Math.min(
                        totalPages,
                        value + 1,
                      ),
                    )
                  }
                >
                  Next
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </>
  );
}