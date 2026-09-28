"use client";
import * as React from "react";

import { compareTableValues } from "@/lib/table-sort";

import { cn } from "@/lib/utils";

type ChildProps = { children?: React.ReactNode; status?: string; value?: string; colSpan?: number; "data-sort-value"?: string | number };
function contentText(node: React.ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(contentText).join(" ");
  if (React.isValidElement<ChildProps>(node)) {
    const p = node.props;
    return String(p["data-sort-value"] ?? p.status ?? p.value ?? contentText(p.children));
  }
  return "";
}
function elements(children: React.ReactNode) {
  return React.Children.toArray(children).filter(React.isValidElement<ChildProps>);
}
function tag(element: React.ReactElement): string {
  return typeof element.type === "string" ? element.type :
    (element.type as { displayName?: string }).displayName ?? "";
}
const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement> & { paginate?: boolean }>(
  ({ className, children, paginate = false, ...props }, ref) => {
    const [sort, setSort] = React.useState<{column: number; desc: boolean} | null>(null);
    const [page, setPage] = React.useState(0);
    const [pageSize, setPageSize] = React.useState(10);
    const body = elements(children).find(section => ["tbody", "TableBody"].includes(tag(section)));
    const bodyRows = elements(body?.props.children);
    const canPage = paginate && !bodyRows.some(row => elements(row.props.children).some(cell => (cell.props.colSpan ?? 1) > 1));
    const total = bodyRows.length;
    const pages = Math.max(1, Math.ceil(total / pageSize));
    const currentPage = Math.min(page, pages - 1);
    const rowKeys = bodyRows.map(row => row.key).join("|");
    React.useEffect(() => setPage(0), [rowKeys]);
    const control = "rounded-md border border-border bg-background px-3 py-2 text-sm hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed";
    const sections = elements(children).map(section => {
      const sectionTag = tag(section);
      if (sectionTag === "thead" || sectionTag === "TableHeader") {
        return React.cloneElement(section, {}, elements(section.props.children).map(row =>
          React.cloneElement(row, {}, elements(row.props.children).map((cell, column) => {
            const label = contentText(cell.props.children).trim();
            if (/^actions?$/i.test(label) || !label) return cell;
            const active = sort?.column === column;
            return React.cloneElement(cell, {
              "aria-sort": active ? sort.desc ? "descending" : "ascending" : "none",
            } as React.HTMLAttributes<HTMLElement>, <button type="button"
              className="inline-flex items-center gap-2 text-left hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
              onClick={() => { setSort({column, desc: active ? !sort.desc : false}); setPage(0); }}
              title={"Sort by " + label}>
              {cell.props.children}<span aria-hidden="true">{active ? sort.desc ? "↓" : "↑" : "↕"}</span>
            </button>);
          }))
        ));
      }
      if ((sectionTag === "tbody" || sectionTag === "TableBody") && (sort || canPage)) {
        const rows = elements(section.props.children);
        if (rows.some(row => elements(row.props.children).some(cell => (cell.props.colSpan ?? 1) > 1))) return section;
        const ordered = rows.map((row, index) => ({row, index})).sort((a,b) => {
          if (!sort) return a.index - b.index;
          const av = contentText(elements(a.row.props.children)[sort.column]);
          const bv = contentText(elements(b.row.props.children)[sort.column]);
          const result = compareTableValues(av,bv);
          return (sort.desc ? -result : result) || a.index-b.index;
        });
        return React.cloneElement(section, {}, (canPage ? ordered.slice(currentPage * pageSize, (currentPage + 1) * pageSize) : ordered).map(item => item.row));
      }
      return section;
    });
    return <div className="w-full"><div className="w-full overflow-auto">
      <table ref={ref} className={cn("w-full caption-bottom text-sm", className)} {...props}>{sections}</table>
    </div>
      {canPage && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-3 py-3">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">Rows per page
          <select aria-label="Rows per page" className={control} value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(0); }}><option value={5}>5</option><option value={10}>10</option></select>
        </label>
        <span className="text-sm text-muted-foreground" role="status">{total ? currentPage * pageSize + 1 : 0}–{Math.min((currentPage + 1) * pageSize, total)} of {total}</span>
        <div className="flex items-center gap-3"><button type="button" className={control} disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span className="text-sm">Page {currentPage + 1} of {pages}</span><button type="button" className={control} disabled={currentPage + 1 >= pages} onClick={() => setPage(currentPage + 1)}>Next</button></div>
      </div>}
    </div>;
  }
);
Table.displayName = "Table";

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
));
TableHeader.displayName = "TableHeader";

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn("[&_tr:last-child]:border-0", className)}
    {...props}
  />
));
TableBody.displayName = "TableBody";

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
      className,
    )}
    {...props}
  />
));
TableRow.displayName = "TableRow";

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "h-10 px-3 text-left align-middle text-xs font-medium uppercase text-muted-foreground",
      className,
    )}
    {...props}
  />
));
TableHead.displayName = "TableHead";

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td ref={ref} className={cn("px-3 py-3 align-middle", className)} {...props} />
));
TableCell.displayName = "TableCell";

export { Table, TableBody, TableCell, TableHead, TableHeader, TableRow };
