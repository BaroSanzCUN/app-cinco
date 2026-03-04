/**
 * Módulo DataTable
 *
 * Componente reutilizable de tabla profesional con arquitectura modular.
 *
 * Estructura:
 * - DataTable.tsx: Componente principal (orquestador)
 * - DataTable.hooks.ts: Lógica de estado y efectos
 * - DataTable.utils.ts: Funciones helper
 * - components/: Sub-componentes especializados
 *   - DataTableToolbar: Barra de herramientas
 *   - DataTableDesktop: Vista desktop
 *   - DataTableMobile: Vista móvil
 *   - DataTablePagination: Controles de paginación
 *   - DataTableColumnVisibility: Dropdown de columnas
 *   - DataTableHeader: Encabezados
 *   - DataTableBody: Cuerpo de tabla
 *
 * Principios aplicados:
 * - Single Responsibility: Cada componente tiene una única responsabilidad
 * - Open/Closed: Extendible mediante props, cerrado a modificación
 * - Separation of Concerns: UI, lógica y utilidades separadas
 * - DRY: No repetición de código entre componentes
 * - Composition over Inheritance: Composición de componentes pequeños
 */

export { DataTable } from "./DataTable";
export * from "./DataTable.utils";
export * from "./DataTable.hooks";
