"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  formatDateTime,
} from "@/lib/datetime";

import {
  Badge,
} from "@/components/ui/badge";


export type ResourceEvent = {
  type: string;
  reason: string;
  message: string;

  count?: number;

  first_timestamp?: string;
  last_timestamp?: string;
};


type Props = {
  events?: ResourceEvent[];
};


export function EventsPanel({
  events = [],
}: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Events
        </CardTitle>
      </CardHeader>

      <CardContent>
        {events.length === 0 ? (
          <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
            No events found.
          </div>
        ) : (
          <div className="space-y-4">
            {events.map(
              (
                event,
                index,
              ) => (
                <div
                  key={`${event.reason}-${event.last_timestamp}-${index}`}
                  className="rounded-lg border p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <Badge
                        variant={
                          event.type === "Warning"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {event.type || "Unknown"}
                      </Badge>

                      <Badge variant="outline">
                        {event.reason || "Event"}
                      </Badge>
                    </div>

                    <div className="text-xs text-muted-foreground">
                      Count: {event.count ?? 1}
                    </div>
                  </div>

                  <div className="mt-3 whitespace-pre-wrap text-sm">
                    {event.message || "-"}
                  </div>

                  <div className="mt-3 flex justify-between gap-4 text-xs text-muted-foreground">
                    <span>
                      First:{" "}
                      {formatDateTime(
                        event.first_timestamp,
                      )}
                    </span>

                    <span>
                      Last:{" "}
                      {formatDateTime(
                        event.last_timestamp,
                      )}
                    </span>
                  </div>
                </div>
              ),
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}