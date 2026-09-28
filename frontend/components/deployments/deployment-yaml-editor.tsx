"use client";

import {
  CheckCircle2,
  Loader2,
  Save,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  useEffect,
  useState,
} from "react";

import { Button } from "@/components/ui/button";

type Props = {
  yaml: string;
  isLoading?: boolean;

  onValidate: (
    yaml: string,
  ) => Promise<unknown>;

  onApply: (
    yaml: string,
  ) => Promise<unknown>;
};

function getMessage(
  result: unknown,
  fallback: string,
): string {
  if (
    result &&
    typeof result === "object"
  ) {
    const data =
      result as Record<string, unknown>;

    if (
      typeof data.message === "string"
    ) {
      return data.message;
    }

    if (
      typeof data.detail === "string"
    ) {
      return data.detail;
    }
  }

  return fallback;
}

export function DeploymentYamlEditor({
  yaml,
  isLoading = false,
  onValidate,
  onApply,
}: Props) {
  const [value, setValue] =
    useState(yaml);

  const [isValidating, setIsValidating] =
    useState(false);

  const [isApplying, setIsApplying] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  const [status, setStatus] =
    useState<"success" | "error" | null>(
      null,
    );

  useEffect(() => {
    setValue(yaml);
  }, [yaml]);

  async function handleValidate() {
    try {
      setIsValidating(true);

      setMessage(null);
      setStatus(null);

      const result =
        await onValidate(value);

      setMessage(
        getMessage(
          result,
          "YAML validation completed successfully.",
        ),
      );

      setStatus("success");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "YAML validation failed.",
      );

      setStatus("error");
    } finally {
      setIsValidating(false);
    }
  }

  async function handleApply() {
    try {
      setIsApplying(true);

      setMessage(null);
      setStatus(null);

      const result =
        await onApply(value);

      setMessage(
        getMessage(
          result,
          "Deployment YAML applied successfully.",
        ),
      );

      setStatus("success");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Failed to apply deployment YAML.",
      );

      setStatus("error");
    } finally {
      setIsApplying(false);
    }
  }

  const busy =
    isLoading ||
    isValidating ||
    isApplying;

  return (
    <div className="space-y-4">

      <div className="flex flex-wrap items-center justify-between gap-3">

        <div>

          <h3 className="text-sm font-semibold">
            Deployment YAML Editor
          </h3>

          <p className="text-xs text-muted-foreground">
            Validate your changes before
            applying them to Kubernetes.
          </p>

        </div>

        <div className="flex gap-2">

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleValidate}
            disabled={busy}
          >
            {isValidating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Validating
              </>
            ) : (
              <>
                <ShieldCheck className="mr-2 h-4 w-4" />
                Validate
              </>
            )}
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleApply}
            disabled={busy}
          >
            {isApplying ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Applying
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Apply
              </>
            )}
          </Button>

        </div>

      </div>

      {message && (

        <div
          className={
            status === "error"
              ? "flex gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
              : "flex gap-2 rounded-md border p-3 text-sm"
          }
        >

          {status === "error" ? (
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          )}

          <span>
            {message}
          </span>

        </div>

      )}

      <textarea
        value={value}
        onChange={(event) =>
          setValue(event.target.value)
        }
        disabled={busy}
        spellCheck={false}
        className="min-h-[650px] w-full resize-y rounded-lg border bg-muted p-4 font-mono text-xs leading-6 outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
      />

    </div>
  );
}