import { AlertCircle, Loader2 } from "lucide-react";

import { errorMessage } from "@/lib/api";

type ResourceStateProps = {
  isLoading?: boolean;
  error?: unknown;
  empty?: boolean;
  emptyLabel?: string;
};

export function ResourceState({
  isLoading,
  error,
  empty,
  emptyLabel = "No records returned.",
}: ResourceStateProps) {
  if (isLoading) {
    return (
      <div className="flex min-h-32 items-center gap-3 rounded-lg border border-border bg-background p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        Loading backend data
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-32 items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" aria-hidden="true" />
        {errorMessage(error)}
      </div>
    );
  }

  if (empty) {
    return (
      <div className="flex min-h-32 items-center rounded-lg border border-border bg-background p-4 text-sm text-muted-foreground">
        {emptyLabel}
      </div>
    );
  }

  return null;
}
