"use client";

import { QueueInvestigation } from "@/components/queue-investigation";
import { SearchCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

type InvestigateButtonProps = {
  namespace: string;
  resourceType: "namespace" | "pod" | "deployment";
  resourceName?: string;
};

type InvestigationResponse = {
  id: string;
};

export function InvestigateButton({
  namespace,
  resourceType,
  resourceName,
}: InvestigateButtonProps) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleInvestigate() {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiFetch<InvestigationResponse>(
        "/v1/investigations",
        {
          method: "POST",
          body: JSON.stringify({
            namespace,
            resource_type: resourceType,
            resource_name: resourceName,
            log_tail: 200,
            include_previous_logs: false,
          }),
        },
      );

      await queryClient.invalidateQueries({ queryKey: ["investigations"] });
      router.push(`/investigations/${result.id}`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Failed to start investigation",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        size="sm"
        variant="outline"
        onClick={handleInvestigate}
        disabled={isLoading}
      >
        <SearchCheck className="mr-2 h-4 w-4" />
        {isLoading ? "Investigating..." : "Investigate"}
      </Button>

      <QueueInvestigation namespace={namespace} resourceType={resourceType} resourceName={resourceName} />
      {error ? (
        <span className="text-xs text-destructive">
          {error}
        </span>
      ) : null}
    </div>
  );
}