"use client";

import {
  Activity,
  Cpu,
  HardDrive,
  Server,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import { Badge } from "@/components/ui/badge";

import { ResourceState } from "@/components/ui/resource-state";
import { YamlViewer } from "@/components/resource/yaml-viewer";
import {
  NodeSummary,
  useNodeDetail,
} from "@/hooks/use-kubernetes";


type Props = {
  node: NodeSummary | null;
};

export function NodeDrawer({
  node,
}: Props) {
  const detail = useNodeDetail(node);
  const metrics = detail.data?.metrics;

  if (!node) return null;

  return (
    <Card className="mt-6">

      <CardHeader>

        <CardTitle>
          {node.name}
        </CardTitle>

      </CardHeader>

      <CardContent>

        <ResourceState
          isLoading={detail.isLoading}
          error={detail.error}
        />

        {detail.data && (

          <Tabs defaultValue="overview">

            <TabsList>

              <TabsTrigger value="overview">
                Overview
              </TabsTrigger>

              <TabsTrigger value="metrics">
                Metrics
              </TabsTrigger>

              <TabsTrigger value="conditions">
                Conditions
              </TabsTrigger>

              <TabsTrigger value="yaml">
                YAML
              </TabsTrigger>

            </TabsList>

            <TabsContent value="overview">

              <div className="grid gap-4 md:grid-cols-2 mt-4">

                <InfoCard
                  icon={<Server className="h-5 w-5" />}
                  title="Role"
                  value={detail.data.roles}
                />

                <InfoCard
                  icon={<Cpu className="h-5 w-5" />}
                  title="Version"
                  value={detail.data.version}
                />

                <InfoCard
                  icon={<Activity className="h-5 w-5" />}
                  title="Health"
                  value={`${detail.data.health_score}%`}
                />

                <InfoCard
                  icon={<HardDrive className="h-5 w-5" />}
                  title="Internal IP"
                  value={detail.data.internal_ip}
                />

              </div>

            </TabsContent>

            <TabsContent value="metrics">

              <div className="grid gap-4">

                <MetricRow
                  label="CPU"
                  value={
                    metrics?.available
                      ? metrics.cpu ?? "-"
                      : "Metrics Server unavailable"
                  }
                />

                <MetricRow
                  label="Memory"
                  value={
                    metrics?.available
                      ? metrics.memory ?? "-"
                      : "Metrics Server unavailable"
                  }
                />

              </div>

            </TabsContent>

            <TabsContent value="conditions">

              <div className="space-y-3">

                {detail.data.conditions.map(
                  (condition) => (

                    <div
                      key={condition.type}
                      className="flex justify-between rounded border p-3"
                    >

                      <div>

                        <div className="font-medium">
                          {condition.type}
                        </div>

                        <div className="text-xs text-muted-foreground">
                          {condition.reason}
                        </div>

                      </div>

                      <Badge>
                        {condition.status}
                      </Badge>

                    </div>

                  ),
                )}

              </div>

            </TabsContent>

            <TabsContent value="yaml">
              <YamlViewer
                yaml={detail.data.yaml}
                fileName={`${node.name}.yaml`}
              />
            </TabsContent>

          </Tabs>

        )}

      </CardContent>

    </Card>
  );
}

function InfoCard({
  icon,
  title,
  value,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
}) {
  return (
    <Card>

      <CardContent className="flex items-center gap-3 pt-6">

        {icon}

        <div>

          <div className="text-xs text-muted-foreground">
            {title}
          </div>

          <div className="font-semibold">
            {value}
          </div>

        </div>

      </CardContent>

    </Card>
  );
}

function MetricRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex justify-between rounded border p-3">

      <span>{label}</span>

      <span className="font-medium">
        {value}
      </span>

    </div>
  );
}