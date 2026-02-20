import { ColumnDef } from "@tanstack/react-table";

interface DataTableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData>[];

  isLoading?: boolean;
  emptyMessage?: string;

  enablePagination?: boolean;
  pageSize?: number;

  enableGlobalFilter?: boolean;
  enableColumnFilters?: boolean;
  enableSorting?: boolean;

  enablePageSizeSelector?: boolean;
  pageSizeOptions?: number[];
}


export type { DataTableProps };
