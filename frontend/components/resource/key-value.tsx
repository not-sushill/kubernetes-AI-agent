"use client";

type Props = {
  label: string;
  value: React.ReactNode;
};

export function KeyValue({
  label,
  value,
}: Props) {
  return (
    <div className="flex items-center justify-between border-b py-2 last:border-0">

      <span className="text-sm text-muted-foreground">
        {label}
      </span>

      <span className="font-medium break-all text-right">
        {value}
      </span>

    </div>
  );
}