import {
  ColumnFiltersState,
  SortingState,
  Table,
  VisibilityState,
} from "@tanstack/react-table";
import { useEffect, useRef } from "react";

/**
 * Hook que sincroniza el estado interno de la tabla con valores controlados externamente.
 * Actualiza el estado local cuando los valores controlados cambian.
 *
 * @template TData - Tipo de datos de la tabla
 */
export const useControlledTableState = <TData>(
  table: Table<TData>,
  {
    globalFilterValue,
    columnFiltersValue,
    sortingValue,
    columnVisibilityValue,
    pageIndexValue,
    pageSizeValue,
    globalFilter,
    columnFilters,
    sorting,
    columnVisibility,
    setGlobalFilter,
    setColumnFilters,
    setSorting,
    setColumnVisibility,
  }: {
    globalFilterValue?: string;
    columnFiltersValue?: ColumnFiltersState;
    sortingValue?: SortingState;
    columnVisibilityValue?: VisibilityState;
    pageIndexValue?: number;
    pageSizeValue?: number;
    globalFilter: string;
    columnFilters: ColumnFiltersState;
    sorting: SortingState;
    columnVisibility: VisibilityState;
    setGlobalFilter: (value: string) => void;
    setColumnFilters: (value: ColumnFiltersState) => void;
    setSorting: (value: SortingState) => void;
    setColumnVisibility: (value: VisibilityState) => void;
  },
) => {
  // Sincronizar globalFilter
  useEffect(() => {
    if (globalFilterValue !== undefined && globalFilterValue !== globalFilter) {
      setGlobalFilter(globalFilterValue);
    }
  }, [globalFilter, globalFilterValue, setGlobalFilter]);

  // Sincronizar columnFilters
  useEffect(() => {
    if (columnFiltersValue !== undefined) {
      setColumnFilters(columnFiltersValue);
    }
  }, [columnFiltersValue, setColumnFilters]);

  // Sincronizar sorting
  useEffect(() => {
    if (sortingValue !== undefined) {
      setSorting(sortingValue);
    }
  }, [sortingValue, setSorting]);

  // Sincronizar columnVisibility
  useEffect(() => {
    if (columnVisibilityValue !== undefined) {
      setColumnVisibility(columnVisibilityValue);
    }
  }, [columnVisibilityValue, setColumnVisibility]);

  // Sincronizar pageIndex
  useEffect(() => {
    if (pageIndexValue !== undefined) {
      const currentPageIndex = table.getState().pagination.pageIndex;
      if (pageIndexValue !== currentPageIndex) {
        table.setPageIndex(pageIndexValue);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageIndexValue]);

  // Sincronizar pageSize
  useEffect(() => {
    if (pageSizeValue !== undefined) {
      const currentPageSize = table.getState().pagination.pageSize;
      if (pageSizeValue !== currentPageSize) {
        table.setPageSize(pageSizeValue);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageSizeValue]);
};

/**
 * Hook que notifica cuando las filas visibles de la tabla cambian.
 * Compara las filas actuales con las anteriores y solo dispara el callback
 * si realmente hay cambios en los datos.
 *
 * @template TData - Tipo de datos de la tabla
 */
export const useVisibleDataChange = <TData>(
  table: Table<TData>,
  data: TData[],
  globalFilter: string,
  columnFilters: ColumnFiltersState,
  sorting: SortingState,
  onVisibleDataChange?: (rows: TData[]) => void,
) => {
  const previousVisibleRowsRef = useRef<TData[]>([]);

  useEffect(() => {
    if (!onVisibleDataChange) {
      return;
    }

    const visibleRows = table.getRowModel().rows.map((row) => row.original);
    const previousRows = previousVisibleRowsRef.current;

    // Optimización: Solo disparar callback si hay cambios reales
    const sameLength = previousRows.length === visibleRows.length;
    const sameReferences =
      sameLength &&
      previousRows.every(
        (previousRow, index) => previousRow === visibleRows[index],
      );

    if (sameReferences) {
      return;
    }

    previousVisibleRowsRef.current = visibleRows;
    onVisibleDataChange(visibleRows);
  }, [onVisibleDataChange, table, data, globalFilter, columnFilters, sorting]);
};
