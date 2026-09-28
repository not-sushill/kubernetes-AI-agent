"use client";

import { ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
};

export function ResourceSection({
  title,
  children,
}: Props) {
  return (
    <div className="space-y-3">

      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>

      <div className="rounded-lg border bg-card p-4">
        {children}
      </div>

    </div>
  );
}