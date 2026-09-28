"use client";
import { formatAge } from "@/lib/datetime";

import {
  Activity,
  Globe,
  Network,
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

import {
  ServiceSummary,
  useServiceYaml,
} from "@/hooks/use-kubernetes";

type Props = {
  service: ServiceSummary | null;
};

export function ServiceDrawer({
  service,
}: Props) {

  const yaml =
    useServiceYaml(service);

  if (!service) {
    return null;
  }

  return (

    <Card className="mt-6">

      <CardHeader>

        <CardTitle>
          {service.name}
        </CardTitle>

      </CardHeader>

      <CardContent>

        <ResourceState
          isLoading={yaml.isLoading}
          error={yaml.error}
        />

        <Tabs defaultValue="overview">

          <TabsList>

            <TabsTrigger value="overview">
              Overview
            </TabsTrigger>

            <TabsTrigger value="ports">
              Ports
            </TabsTrigger>

            <TabsTrigger value="selectors">
              Selectors
            </TabsTrigger>

            <TabsTrigger value="yaml">
              YAML
            </TabsTrigger>

          </TabsList>

          <TabsContent
            value="overview"
            className="mt-6"
          >

            <div className="grid gap-4 md:grid-cols-2">

              <InfoCard
                icon={
                  <Server className="h-5 w-5" />
                }
                title="Type"
                value={service.type}
              />

              <InfoCard
                icon={
                  <Network className="h-5 w-5" />
                }
                title="Cluster IP"
                value={
                  service.cluster_ip ||
                  "-"
                }
              />

              <InfoCard
                icon={
                  <Globe className="h-5 w-5" />
                }
                title="Namespace"
                value={
                  service.namespace
                }
              />

              <InfoCard
                icon={
                  <Activity className="h-5 w-5" />
                }
                title="Age"
                value={
                  formatAge(service.age)
                }
              />

            </div>

          </TabsContent>

                    <TabsContent
            value="ports"
            className="mt-6"
          >

            <div className="space-y-4">

              {service.ports.length === 0 ? (

                <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
                  No ports exposed.
                </div>

              ) : (

                service.ports.map(
                  (
                    port,
                    index,
                  ) => (

                    <Card
                      key={index}
                    >

                      <CardContent className="pt-6">

                        <div className="grid gap-4 md:grid-cols-4">

                          <MetricCard
                            title="Name"
                            value={
                              port.name ||
                              "-"
                            }
                          />

                          <MetricCard
                            title="Port"
                            value={String(
                              port.port,
                            )}
                          />

                          <MetricCard
                            title="Target"
                            value={String(
                              port.target_port,
                            )}
                          />

                          <MetricCard
                            title="Protocol"
                            value={
                              port.protocol
                            }
                          />

                        </div>

                      </CardContent>

                    </Card>

                  ),
                )

              )}

            </div>

          </TabsContent>

          <TabsContent
            value="selectors"
            className="mt-6"
          >

            {Object.keys(
              service.selector,
            ).length === 0 ? (

              <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">

                No selectors configured.

              </div>

            ) : (

              <div className="flex flex-wrap gap-2">

                {Object.entries(
                  service.selector,
                ).map(
                  (
                    [
                      key,
                      value,
                    ],
                  ) => (

                    <Badge
                      key={key}
                      variant="secondary"
                    >

                      {key}={value}

                    </Badge>

                  ),
                )}

              </div>

            )}

          </TabsContent>
                    <TabsContent
            value="yaml"
            className="mt-6"
          >

            <pre className="max-h-[650px] overflow-auto rounded-md border bg-muted p-4 text-xs font-mono">

{yaml.data?.yaml ?? ""}

            </pre>

          </TabsContent>

        </Tabs>

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

          <div className="font-semibold break-all">
            {value}
          </div>

        </div>

      </CardContent>

    </Card>

  );

}

function MetricCard({
  title,
  value,
}: {
  title: string;
  value: string;
}) {

  return (

    <div className="rounded-md border p-4">

      <div className="text-xs text-muted-foreground">

        {title}

      </div>

      <div className="mt-2 text-lg font-semibold">

        {value}

      </div>

    </div>

  );

}