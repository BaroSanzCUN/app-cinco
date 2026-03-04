import { Table, Column } from "@tanstack/react-table";
import Input from "@/components/form/input/InputField";
import { DataTableColumnVisibility } from "./DataTableColumnVisibility";

interface DataTableToolbarProps<TData> {
  table: Table<TData>;
  enableGlobalFilter: boolean;
  enableColumnVisibility: boolean;
  globalFilterPlaceholder: string;
  toolbarActions?: React.ReactNode;
}

/**
 * Componente de barra de herramientas de la tabla.
 * Incluye el buscador global, controles de visibilidad de columnas y acciones personalizadas.
 *
 * @template TData - Tipo de datos de la tabla
 */
export function DataTableToolbar<TData>({
  table,
  enableGlobalFilter,
  enableColumnVisibility,
  globalFilterPlaceholder,
  toolbarActions,
}: DataTableToolbarProps<TData>) {
  const shouldRenderToolbar =
    enableGlobalFilter || enableColumnVisibility || toolbarActions;

  if (!shouldRenderToolbar) {
    return null;
  }

  const allColumns = table.getAllLeafColumns() as Column<TData, unknown>[];

  return (
    <div className="flex flex-col gap-3 border-b border-gray-100 p-4 md:flex-row md:items-center md:justify-between dark:border-white/5">
      <div className="flex w-full flex-wrap items-center gap-2 md:w-auto">
        {enableGlobalFilter && (
          <Input
            type="search"
            placeholder={globalFilterPlaceholder}
            value={table.getState().globalFilter ?? ""}
            onChange={(e) => table.setGlobalFilter(e.target.value)}
            className="w-full md:w-72"
          />
        )}
        {toolbarActions}
      </div>

      {enableColumnVisibility && (
        <DataTableColumnVisibility columns={allColumns} />
      )}
    </div>
  );
}
