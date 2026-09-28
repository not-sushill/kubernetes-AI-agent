"use client";

import {
  Check,
  Loader2,
  RotateCcw,
  Save,
  ShieldCheck,
} from "lucide-react";
import {
  useEffect,
  useState,
} from "react";

import { Button } from "@/components/ui/button";

type DeploymentYamlEditorProps = {
  namespace: string;
  deployment: string;
  initialYaml: string;
  onValidate: (yaml: string) => Promise<{
    valid: boolean;
    message: string;
  }>;
  onApply: (yaml: string) => Promise<{
    success: boolean;
    message: string;
    backup_id?: string | null;
  }>;
  isValidating?: boolean;
  isApplying?: boolean;
};

export function DeploymentYamlEditor({
  namespace,
  deployment,
  initialYaml,
  onValidate,
  onApply,
  isValidating = false,
  isApplying = false,
}: DeploymentYamlEditorProps) {
  const [yaml, setYaml] = useState(initialYaml);
  const [message, setMessage] = useState<string | null>(
    null,
  );
  const [isValid, setIsValid] = useState<boolean | null>(
    null,
  );

  useEffect(() => {
    setYaml(initialYaml);
    setMessage(null);
    setIsValid(null);
  }, [initialYaml, namespace, deployment]);

  const hasChanges = yaml !== initialYaml;

  async function handleValidate() {
    setMessage(null);

    try {
      const result = await onValidate(yaml);

      setIsValid(result.valid);
      setMessage(result.message);
    } catch (error) {
      setIsValid(false);

      setMessage(
        error instanceof Error
          ? error.message
          : "YAML validation failed.",
      );
    }
  }

  async function handleApply() {
    const confirmed = window.confirm(
      `Apply changes to deployment "${deployment}" in namespace "${namespace}"?`,
    );

    if (!confirmed) {
      return;
    }

    setMessage(null);

    try {
      const result = await onApply(yaml);

      setIsValid(true);
      setMessage(result.message);
    } catch (error) {
      setIsValid(false);

      setMessage(
        error instanceof Error
          ? error.message
          : "Failed to apply deployment YAML.",
      );
    }
  }

  function handleReset() {
    setYaml(initialYaml);
    setMessage(null);
    setIsValid(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">
            Deployment YAML Editor
          </h3>

          <p className="text-xs text-muted-foreground">
            {namespace} / {deployment}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleReset}
            disabled={
              !hasChanges ||
              isValidating ||
              isApplying
            }
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset
          </Button>

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleValidate}
            disabled={
              isValidating ||
              isApplying
            }
          >
            {isValidating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ShieldCheck className="mr-2 h-4 w-4" />
            )}

            Validate
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleApply}
            disabled={
              !hasChanges ||
              isValidating ||
              isApplying
            }
          >
            {isApplying ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}

            Apply Changes
          </Button>
        </div>
      </div>

      {message ? (
        <div
          className={[
            "rounded-md border p-3 text-sm",
            isValid === true
              ? "border-green-500/40 bg-green-500/10"
              : isValid === false
                ? "border-destructive/40 bg-destructive/10"
                : "",
          ].join(" ")}
        >
          {isValid === true ? (
            <Check className="mr-2 inline h-4 w-4" />
          ) : null}

          {message}
        </div>
      ) : null}

      <textarea
        value={yaml}
        onChange={(event) => {
          setYaml(event.target.value);
          setMessage(null);
          setIsValid(null);
        }}
        spellCheck={false}
        className="min-h-[650px] w-full resize-y rounded-lg border bg-muted p-4 font-mono text-xs leading-6 outline-none focus:ring-2 focus:ring-ring"
      />

      <p className="text-xs text-muted-foreground">
        Changes are validated before applying. The backend creates
        a deployment backup before the update.
      </p>
    </div>
  );
}