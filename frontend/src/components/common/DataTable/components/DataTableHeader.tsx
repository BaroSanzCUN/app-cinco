import { HeaderGroup, flexRender } from "@tanstack/react-table";
import { TableCell, TableHeader, TableRow } from "@/components/ui/table";
import Input from "@/components/form/input/InputField";
import { getSortIndicator } from "../DataTable.utils";

interface DataTableHeaderProps<TData> {
  headerGroups: HeaderGroup<TData>[];
  enableSorting: boolean;
  enableColumnFilters: boolean;
}

/**
 * Componente que renderiza el header de la tabla (desktop).
 * Incluye soporte para ordenamiento y filtros por columna.
 *
 * @template TData - Tipo de datos de la tabla
 */
export function DataTableHeaderComponent<TData>({
  headerGroups,
  enableSorting,
  enableColumnFilters,
}: DataTableHeaderProps<TData>) {
  return (
    <TableHeader className="border-b border-gray-100 bg-white dark:border-white/5 dark:bg-gray-900">
      {headerGroups.map((headerGroup) => (
        <TableRow key={headerGroup.id} className="bg-white dark:bg-gray-900">
          {headerGroup.headers.map((header) => (
            <TableCell
              key={header.id}
              isHeader
              className="sticky top-0 z-20 min-w-max bg-white text-theme-xs px-5 py-3 text-start font-medium text-gray-500 dark:bg-gray-900 dark:text-gray-400"
            >
              {header.isPlaceholder ? null : (
                <>
                  <button
                    type="button"
                    className={`w-full text-left ${
                      enableSorting && header.column.getCanSort()
                        ? "cursor-pointer select-none"
                        : "cursor-default"
                    }`}
                    onClick={
                      enableSorting && header.column.getCanSort()
                        ? header.column.getToggleSortingHandler()
                        : undefined
                    }
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )}
                    {enableSorting &&
                      header.column.getCanSort() &&
                      ` ${getSortIndicator(header.column.getIsSorted())}`}
                  </button>

                  {enableColumnFilters && header.column.getCanFilter() && (
                    <div className="mt-1">
                      <Input
                        type="search"
                        value={(header.column.getFilterValue() as string) ?? ""}
                        onChange={(e) =>
                          header.column.setFilterValue(e.target.value)
                        }
                        placeholder="Filtrar..."
                        className="w-full"
                      />
                    </div>
                  )}
                </>
              )}
            </TableCell>
          ))}
        </TableRow>
      ))}
    </TableHeader>
  );
}
