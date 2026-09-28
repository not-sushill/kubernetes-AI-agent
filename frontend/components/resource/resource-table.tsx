"use client";

import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Column = {
  title: string;
  className?: string;
};

type Props<T> = {
  columns: Column[];
  rows: T[];
  rowKey: (row: T) => string;
  renderRow: (row: T) => React.ReactNode;
};

export function ResourceTable<T>({
  columns,
  rows,
  rowKey,
  renderRow,
}: Props<T>) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead
              key={column.title}
              className={column.className}
            >
              {column.title}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>

      <TableBody>
        {rows.map((row) => (
          <TableRow key={rowKey(row)}>
            {renderRow(row)}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}