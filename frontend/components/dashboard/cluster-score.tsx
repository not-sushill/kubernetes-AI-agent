"use client";

import { Activity } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Progress } from "@/components/ui/progress";

type Props = {
  score: number;
  healthyPods: number;
  totalPods: number;
  readyDeployments: number;
  totalDeployments: number;
  readyNodes: number;
  totalNodes: number;
};

export function ClusterScore({
  score,
  healthyPods,
  totalPods,
  readyDeployments,
  totalDeployments,
  readyNodes,
  totalNodes,
}: Props) {
  return (
    <Card className="h-full min-w-0">

      <CardHeader>

        <CardTitle className="flex items-center gap-2">

          <Activity className="h-5 w-5" />

          Cluster Health

        </CardTitle>

      </CardHeader>

      <CardContent className="space-y-5">

        <div>

          <div className="flex justify-between mb-2">

            <span className="text-sm text-muted-foreground">
              Overall Score
            </span>

            <span className="font-bold text-xl">
              {score}%
            </span>

          </div>

          <Progress value={score} />

        </div>

        <HealthRow
          label="Pods"
          current={healthyPods}
          total={totalPods}
        />

        <HealthRow
          label="Deployments"
          current={readyDeployments}
          total={totalDeployments}
        />

        <HealthRow
          label="Nodes"
          current={readyNodes}
          total={totalNodes}
        />

      </CardContent>

    </Card>
  );
}

function HealthRow({
  label,
  current,
  total,
}: {
  label: string;
  current: number;
  total: number;
}) {
  const percent =
    total === 0
      ? 0
      : Math.round((current / total) * 100);

  return (
    <div className="space-y-1">

      <div className="flex justify-between text-sm">

        <span>{label}</span>

        <span>
          {current}/{total}
        </span>

      </div>

      <Progress value={percent} />

    </div>
  );
}