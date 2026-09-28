"use client";

import { Check, Copy, Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

type Props = {
  yaml: string;
  fileName?: string;
};

export function YamlViewer({
  yaml,
  fileName = "resource.yaml",
}: Props) {
  const [copied, setCopied] = useState(false);

  async function copyYaml() {
    await navigator.clipboard.writeText(yaml);

    setCopied(true);

    setTimeout(() => {
      setCopied(false);
    }, 2000);
  }

  function downloadYaml() {
    const blob = new Blob([yaml], {
      type: "text/yaml",
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;

    link.download = fileName;

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-3">

      <div className="flex justify-end gap-2">

        <Button
          size="sm"
          variant="outline"
          onClick={copyYaml}
        >
          {copied ? (
            <>
              <Check className="mr-2 h-4 w-4" />
              Copied
            </>
          ) : (
            <>
              <Copy className="mr-2 h-4 w-4" />
              Copy
            </>
          )}
        </Button>

        <Button
          size="sm"
          variant="outline"
          onClick={downloadYaml}
        >
          <Download className="mr-2 h-4 w-4" />
          Download
        </Button>

      </div>

      <pre className="max-h-[700px] overflow-auto rounded-lg border bg-muted p-4 font-mono text-xs leading-6">
        {yaml}
      </pre>

    </div>
  );
}