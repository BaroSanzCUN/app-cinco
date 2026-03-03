import { Row, flexRender } from "@tanstack/react-table";
import { TableBody, TableCell, TableRow } from "@/components/ui/table";

interface DataTableBodyProps<TData> {
  rows: Row<TData>[];
  visibleColumnsCount: number;
  isLoading: boolean;
  emptyMessage: string;
  onRowClick?: (row: TData) => void;
}

/**
 * Componente que renderiza el cuerpo de la tabla (desktop).
 * Maneja estados de carga, vacío y renderiza las filas de datos.
 *
 * @template TData - Tipo de datos de la tabla
 */
export function DataTableBodyComponent<TData>({
  rows,
  visibleColumnsCount,
  isLoading,
  emptyMessage,
  onRowClick,
}: DataTableBodyProps<TData>) {
  return (
    <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
      {isLoading ? (
        <TableRow>
          <TableCell
            colSpan={visibleColumnsCount || 1}
            className="px-6 py-8 text-center text-gray-500"
          >
            Loading...
          </TableCell>
        </TableRow>
      ) : rows.length === 0 ? (
        <TableRow>
          <TableCell
            colSpan={visibleColumnsCount || 1}
            className="px-6 py-8 text-center text-gray-500"
          >
            {emptyMessage}
          </TableCell>
        </TableRow>
      ) : (
        rows.map((row) => (
          <TableRow
            key={row.id}
            className={onRowClick ? "cursor-pointer" : undefined}
            onClick={onRowClick ? () => onRowClick(row.original) : undefined}
          >
            {row.getVisibleCells().map((cell) => (
              <TableCell
                key={cell.id}
                className="min-w-max text-theme-sm px-4 py-3 text-start text-gray-500 dark:text-gray-400"
              >
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))
      )}
    </TableBody>
  );
}
