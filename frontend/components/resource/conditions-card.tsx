"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";

export type ResourceCondition = {
  type: string;
  status: string;
  reason?: string;
  message?: string;
  last_transition_time?: string;
};

type Props = {
  conditions?: ResourceCondition[];
};

export function ConditionsCard({
  conditions = [],
}: Props) {

  return (

    <Card>

      <CardHeader>

        <CardTitle>

          Conditions

        </CardTitle>

      </CardHeader>

      <CardContent>

        {conditions.length === 0 ? (

          <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">

            No conditions available.

          </div>

        ) : (

          <div className="space-y-3">

            {conditions.map(
              (
                condition,
              ) => (

                <div
                  key={condition.type}
                  className="rounded-md border p-4"
                >

                  <div className="flex items-center justify-between">

                    <div className="font-medium">

                      {condition.type}

                    </div>

                    <Badge
                      variant={
                        condition.status === "True"
                          ? "default"
                          : "secondary"
                      }
                    >

                      {condition.status}

                    </Badge>

                  </div>

                  {condition.reason && (

                    <div className="mt-2 text-sm font-medium">

                      {condition.reason}

                    </div>

                  )}

                  {condition.message && (

                    <div className="mt-1 text-sm text-muted-foreground whitespace-pre-wrap">

                      {condition.message}

                    </div>

                  )}

                  {condition.last_transition_time && (

                    <div className="mt-3 text-xs text-muted-foreground">

                      Last Transition:{" "}

                      {condition.last_transition_time}

                    </div>

                  )}

                </div>

              ),
            )}

          </div>

        )}

      </CardContent>

    </Card>

  );

}