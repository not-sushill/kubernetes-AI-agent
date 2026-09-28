"use client";

import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { NamespaceSummary } from "@/hooks/use-kubernetes";

type NamespaceFilterProps = {
  namespaces?: NamespaceSummary[];
  value: string;
  onChange: (value: string) => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
};

export function NamespaceFilter({
  namespaces,
  value,
  onChange,
  onRefresh,
  isRefreshing,
}: NamespaceFilterProps) {
  return (
    <>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 min-w-44 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <option value="all">All namespaces</option>
        {(namespaces ?? []).map((namespace) => (
          <option key={namespace.name} value={namespace.name}>
            {namespace.name}
          </option>
        ))}
      </select>
      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={onRefresh}
        disabled={isRefreshing}
        aria-label="Refresh"
      >
        <RefreshCw
          className={isRefreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"}
          aria-hidden="true"
        />
      </Button>
    </>
  );
}
