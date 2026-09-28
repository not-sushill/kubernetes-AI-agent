"use client";

import { ReactNode } from "react";

type ResourceHeaderProps = {
  title: string;
  subtitle?: string;
  status?: ReactNode;
  actions?: ReactNode;
};

export function ResourceHeader({
  title,
  subtitle,
  status,
  actions,
}: ResourceHeaderProps) {
  return (
    <div className="flex items-start justify-between border-b pb-4">

      <div>

        <h2 className="text-xl font-semibold">
          {title}
        </h2>

        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">
            {subtitle}
          </p>
        )}

      </div>

      <div className="flex items-center gap-2">
        {status}
        {actions}
      </div>

    </div>
  );
}