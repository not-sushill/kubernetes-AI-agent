import { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type MetricCardProps = {
  title: string;
  value: string | number;
  icon: LucideIcon;
  tone?: "default" | "success" | "warning" | "destructive";
  detail?: string;
};

const toneClasses = {
  default: "bg-secondary text-secondary-foreground",
  success: "bg-success/10 text-success",
  warning: "bg-warning/15 text-foreground",
  destructive: "bg-destructive/10 text-destructive",
};

export function MetricCard({
  title,
  value,
  icon: Icon,
  tone = "default",
  detail,
}: MetricCardProps) {
  return (
    <Card className="h-full transition-shadow group-hover:shadow-md">
      <CardHeader className="flex flex-row items-center justify-between gap-3 pb-2">
        <CardTitle className="text-muted-foreground">{title}</CardTitle>
        <span
          className={cn(
            "inline-flex h-10 w-10 items-center justify-center rounded-md",
            toneClasses[tone],
          )}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
        {detail ? (
          <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}
