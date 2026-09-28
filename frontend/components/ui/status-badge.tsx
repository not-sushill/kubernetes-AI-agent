import { Badge } from "@/components/ui/badge";

type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  const variant =
    normalized === "running" ||
    normalized === "active" ||
    normalized === "true" ||
    normalized === "healthy"
      ? "success"
      : normalized === "pending" || normalized === "unknown"
        ? "warning"
        : normalized === "failed" || normalized === "false"
          ? "destructive"
          : "outline";

  return <Badge variant={variant}>{status || "unknown"}</Badge>;
}
