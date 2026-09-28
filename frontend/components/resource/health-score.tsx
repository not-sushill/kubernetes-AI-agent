"use client";

import { Progress } from "@/components/ui/progress";

type Props = {
  score: number;
};

export function HealthScore({
  score,
}: Props) {

  const color =
    score >= 90
      ? "text-green-500"
      : score >= 70
      ? "text-yellow-500"
      : "text-red-500";

  return (
    <div className="space-y-2">

      <div className="flex items-center justify-between">

        <span className="text-sm text-muted-foreground">
          Cluster Health
        </span>

        <span className={`font-bold ${color}`}>
          {score}%
        </span>

      </div>

      <Progress value={score} />

    </div>
  );
}