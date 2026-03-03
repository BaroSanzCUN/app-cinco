import { Table as ReactTable } from "@tanstack/react-table";

interface DataTablePaginationProps<TData> {
  table: ReactTable<TData>;
  enablePageSizeSelector: boolean;
  pageSizeOptions: number[];
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
}

/**
 * Componente que renderiza los controles de paginación de la tabla.
 * Incluye selector de tamaño de página, botones de navegación e información de página actual.
 *
 * @template TData - Tipo de datos de la tabla
 */
export function DataTablePagination<TData>({
  table,
  enablePageSizeSelector,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
}: DataTablePaginationProps<TData>) {
  const currentPageIndex = table.getState().pagination.pageIndex;
  const currentPageSize = table.getState().pagination.pageSize;
  const pageCount = table.getPageCount();

  const handlePreviousPage = () => {
    if (!table.getCanPreviousPage()) return;
    const nextPage = Math.max(currentPageIndex - 1, 0);
    table.setPageIndex(nextPage);
    onPageChange?.(nextPage);
  };

  const handleNextPage = () => {
    if (!table.getCanNextPage()) return;
    const maxPage = Math.max(pageCount - 1, 0);
    const nextPage = Math.min(currentPageIndex + 1, maxPage);
    table.setPageIndex(nextPage);
    onPageChange?.(nextPage);
  };

  const handlePageSizeChange = (size: number) => {
    table.setPageSize(size);
    onPageSizeChange?.(size);
    // Resetear a la primera página después de cambiar el tamaño
    table.setPageIndex(0);
    onPageChange?.(0);
  };

  return (
    <div className="flex items-center justify-between border-t px-5 py-4">
      <div className="flex w-full items-center justify-between gap-3">
        {enablePageSizeSelector && pageSizeOptions && (
          <select
            value={currentPageSize}
            onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            className="rounded border px-2 py-1 text-sm focus:ring-1 focus:ring-brand-500/10 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        )}

        <div className="flex items-center gap-2">
          <button
            onClick={handlePreviousPage}
            disabled={!table.getCanPreviousPage()}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-500">
            Página {currentPageIndex + 1} de {pageCount}
          </span>
          <button
            onClick={handleNextPage}
            disabled={!table.getCanNextPage()}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  );
}
