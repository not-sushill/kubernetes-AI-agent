"use client";

import { ReactNode } from "react";

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

import { ResourceState } from "@/components/ui/resource-state";

export type ResourceTab = {
  value: string;
  label: string;
  content: ReactNode;
};

type Props = {
  title: string;
  subtitle?: string;
  isLoading?: boolean;
  error?: unknown;
  defaultTab?: string;
  tabs: ResourceTab[];
};

export function ResourceDrawer({
  title,
  subtitle,
  isLoading = false,
  error,
  defaultTab,
  tabs,
}: Props) {
  return (
    <Card className="mt-6">

      <CardHeader>

        <div className="flex flex-col gap-1">

          <CardTitle>
            {title}
          </CardTitle>

          {subtitle && (
            <p className="text-sm text-muted-foreground">
              {subtitle}
            </p>
          )}

        </div>

      </CardHeader>

      <CardContent>

        <ResourceState
          isLoading={isLoading}
          error={error}
        />

        {!isLoading && !error && (

          <Tabs
            defaultValue={
              defaultTab ??
              tabs[0]?.value
            }
          >

            <TabsList>

              {tabs.map((tab) => (

                <TabsTrigger
                  key={tab.value}
                  value={tab.value}
                >
                  {tab.label}
                </TabsTrigger>

              ))}

            </TabsList>

            {tabs.map((tab) => (

              <TabsContent
                key={tab.value}
                value={tab.value}
                className="mt-6"
              >

                {tab.content}

              </TabsContent>

            ))}

          </Tabs>

        )}

      </CardContent>

    </Card>
  );
}