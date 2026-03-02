import { Row, Updater, flexRender } from "@tanstack/react-table";

/**
 * Extrae el siguiente estado de un Updater, que puede ser un valor directo
 * o una función que toma el estado anterior y retorna el nuevo estado.
 *
 * @template TState - Tipo del estado
 * @param updater - Valor directo o función updater
 * @param previous - Estado anterior
 * @returns Nuevo estado
 */
export const getNextState = <TState,>(
  updater: Updater<TState>,
  previous: TState,
): TState => {
  if (typeof updater === "function") {
    return (updater as (old: TState) => TState)(previous);
  }

  return updater as TState;
};

/**
 * Retorna el indicador visual de ordenamiento para una columna.
 *
 * @param sortState - Estado actual de ordenamiento de la columna
 * @returns String con el indicador (↑, ↓ o vacío)
 */
export const getSortIndicator = (sortState: false | "asc" | "desc"): string => {
  if (sortState === "asc") {
    return "↑";
  }

  if (sortState === "desc") {
    return "↓";
  }

  return "";
};

/**
 * Renderiza el valor de una celda específica para la vista móvil.
 * Busca la celda correspondiente por columnId y renderiza su contenido.
 *
 * @template TData - Tipo de datos de la fila
 * @param row - Fila de la tabla
 * @param columnId - ID de la columna a renderizar
 * @returns React node con el contenido renderizado o null si no existe
 */
export const renderMobileCellValue = <TData,>(
  row: Row<TData>,
  columnId: string,
): React.ReactNode => {
  const cell = row
    .getVisibleCells()
    .find((visibleCell) => visibleCell.column.id === columnId);

  if (!cell) {
    return null;
  }

  return flexRender(cell.column.columnDef.cell, cell.getContext());
};

/**
 * Obtiene el label del header de una columna.
 * Si el header es un string, lo retorna directamente.
 * Si no, retorna el id de la columna.
 *
 * @param header - Definición del header
 * @param columnId - ID de la columna (fallback)
 * @returns Label del header como string
 */
export const getColumnHeaderLabel = (
  header: unknown,
  columnId: string,
): string => {
  return typeof header === "string" ? header : columnId;
};
