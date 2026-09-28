"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { KeyValue } from "@/components/resource/key-value";

export type MetadataCardProps = {
  name?: string;
  namespace?: string;
  uid?: string;
  created?: string;
  resourceVersion?: string;
  labels?: number;
  annotations?: number;
};

export function MetadataCard({
  name,
  namespace,
  uid,
  created,
  resourceVersion,
  labels,
  annotations,
}: MetadataCardProps) {
  return (
    <Card>

      <CardHeader>

        <CardTitle>
          Metadata
        </CardTitle>

      </CardHeader>

      <CardContent className="space-y-2">

        <KeyValue
          label="Name"
          value={name ?? "-"}
        />

        <KeyValue
          label="Namespace"
          value={namespace ?? "-"}
        />

        <KeyValue
          label="UID"
          value={uid ?? "-"}
        />

        <KeyValue
          label="Created"
          value={created ?? "-"}
        />

        <KeyValue
          label="Resource Version"
          value={
            resourceVersion ?? "-"
          }
        />

        <KeyValue
          label="Labels"
          value={String(labels ?? 0)}
        />

        <KeyValue
          label="Annotations"
          value={String(annotations ?? 0)}
        />

      </CardContent>

    </Card>
  );
}