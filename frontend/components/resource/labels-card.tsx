"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";

type Props = {
  labels?: Record<string, string>;
};

export function LabelsCard({
  labels = {},
}: Props) {

  const entries =
    Object.entries(labels);

  return (

    <Card>

      <CardHeader>

        <CardTitle>
          Labels
        </CardTitle>

      </CardHeader>

      <CardContent>

        {entries.length === 0 ? (

          <div className="text-sm text-muted-foreground">
            No labels
          </div>

        ) : (

          <div className="flex flex-wrap gap-2">

            {entries.map(
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

      </CardContent>

    </Card>

  );

}