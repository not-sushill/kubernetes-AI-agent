"use client";

import {
  Download,
  RefreshCw,
  Search,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = {
  search: string;
  onSearch: (value: string) => void;

  onRefresh?: () => void;

  onExport?: () => void;

  loading?: boolean;

  placeholder?: string;
};

export function ResourceToolbar({
  search,
  onSearch,
  onRefresh,
  onExport,
  loading = false,
  placeholder = "Search...",
}: Props) {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">

      <div className="relative w-full md:w-96">

        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

        <Input
          value={search}
          onChange={(e) =>
            onSearch(e.target.value)
          }
          placeholder={placeholder}
          className="pl-9"
        />

      </div>

      <div className="flex gap-2">

        {onRefresh && (
          <Button
            variant="outline"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${
                loading
                  ? "animate-spin"
                  : ""
              }`}
            />
            Refresh
          </Button>
        )}

        {onExport && (
          <Button
            variant="outline"
            onClick={onExport}
          >
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        )}

      </div>

    </div>
  );
}