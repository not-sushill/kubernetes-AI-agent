"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";

type Props = {
  selectors?: Record<string, string>;
};

export function SelectorsCard({
  selectors = {},
}: Props) {

  const entries =
    Object.entries(selectors);

  return (

    <Card>

      <CardHeader>

        <CardTitle>
          Selectors
        </CardTitle>

      </CardHeader>

      <CardContent>

        {entries.length === 0 ? (

          <div className="text-sm text-muted-foreground">
            No selectors
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
                  variant="outline"
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