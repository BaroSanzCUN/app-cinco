# Guía de Uso: DataTable Reutilizable

## Visión General

El componente `DataTable` es una tabla profesional y completamente reutilizable que incluye:
- ✅ Filtrado global
- ✅ Ordenamiento por columnas
- ✅ Visibilidad de columnas (show/hide)
- ✅ Paginación configurable
- ✅ Vista responsive para móviles
- ✅ Sincronización automática con URL
- ✅ Exportación a CSV
- ✅ Acciones personalizadas en toolbar

## Patrón de Implementación

### 1. Estructura de Archivos

Para un nuevo módulo (ej: `vehiculos`), crea:

```
src/modules/vehiculos/
  ├── index.tsx                    # Vista principal
  ├── vehiculoTable.utils.ts       # Configuración específica del módulo
  └── vehiculosColumns.tsx         # Definición de columnas
```

### 2. Configuración del Módulo (`vehiculoTable.utils.ts`)

Define las columnas CSV y configuración específica:

```typescript
import { CsvColumn } from "@/utils/csv";
import { VehiculoFormData } from "@/schemas/vehiculos.schema";

// Configuración de columnas para exportación CSV
export const vehiculoCsvColumns: CsvColumn<VehiculoFormData>[] = [
  {
    header: "ID",
    accessor: (row) => row.id,
  },
  {
    header: "Placa",
    accessor: (row) => row.placa,
  },
  {
    header: "Marca",
    accessor: (row) => row.marca,
  },
  {
    header: "Modelo",
    accessor: (row) => row.modelo,
  },
  {
    header: "Año",
    accessor: (row) => row.anio,
  },
  // Campos anidados
  {
    header: "Conductor",
    accessor: (row) => row.conductor_snapshot?.nombre,
  },
];

// Configuración constante del módulo
export const VEHICULO_TABLE_CONFIG = {
  defaultPageSize: 10,
  defaultPageIndex: 0,
  csvFileName: "vehiculos_export.csv",
};
```

### 3. Definición de Columnas (`vehiculosColumns.tsx`)

```typescript
import { ColumnDef } from "@tanstack/react-table";
import { VehiculoFormData } from "@/schemas/vehiculos.schema";
import Badge from "@/components/ui/badge/Badge";

export const vehiculosColumns: ColumnDef<VehiculoFormData>[] = [
  {
    id: "acciones",
    header: "ACCIONES",
    enableSorting: false,
    enableColumnFilter: false,
    enableHiding: false,
    cell: ({ row }) => (
      <div className="flex gap-2">
        {/* Botones de acción */}
      </div>
    ),
  },
  {
    accessorKey: "placa",
    header: "PLACA",
    enableSorting: true,
    enableColumnFilter: true,
  },
  {
    accessorKey: "marca",
    header: "MARCA",
    enableSorting: true,
  },
  {
    accessorKey: "modelo",
    header: "MODELO",
    enableSorting: true,
  },
  {
    id: "estado",
    header: "ESTADO",
    accessorKey: "estado",
    enableSorting: true,
    cell: ({ row }) => {
      const estado = row.original.estado;
      const variant = 
        estado === "activo" ? "success" :
        estado === "inactivo" ? "danger" : "warning";
      
      return <Badge variant={variant}>{estado}</Badge>;
    },
  },
];
```

### 4. Vista Principal (`index.tsx`)

```typescript
"use client";

import { useEffect, useMemo, useState } from "react";
import { DataTable } from "@/components/common/DataTable";
import { useTableUrlState } from "@/hooks/useTableUrlState";
import { exportToCsv } from "@/utils/csv";
import { useVehiculoStore } from "@/store/vehiculo.store";
import Button from "@/components/ui/button/Button";
import { DownloadIcon, PlusIcon } from "@/icons";
import { 
  vehiculoCsvColumns, 
  VEHICULO_TABLE_CONFIG 
} from "./vehiculoTable.utils";
import { vehiculosColumns } from "./vehiculosColumns";
import { VehiculoFormData } from "@/schemas/vehiculos.schema";

const GestionVehiculosView = () => {
  const { loadVehiculos, vehiculos } = useVehiculoStore();
  const [visibleRows, setVisibleRows] = useState<VehiculoFormData[]>([]);

  // Hook genérico para manejo de estado con URL
  const {
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  } = useTableUrlState({
    defaultPageSize: VEHICULO_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: VEHICULO_TABLE_CONFIG.defaultPageIndex,
  });

  useEffect(() => {
    loadVehiculos();
  }, [loadVehiculos]);

  // Handler para exportación CSV
  const handleExportCsv = () => {
    if (!visibleRows.length) return;

    exportToCsv(visibleRows, {
      fileName: VEHICULO_TABLE_CONFIG.csvFileName,
      columns: vehiculoCsvColumns,
    });
  };

  // Acciones del toolbar
  const toolbarActions = (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={handleExportCsv}
        startIcon={<DownloadIcon className="h-4 w-4" />}
        disabled={!visibleRows.length}
      >
        Exportar CSV
      </Button>
      <Button
        variant="primary"
        size="sm"
        startIcon={<PlusIcon />}
      >
        Nuevo Vehículo
      </Button>
    </>
  );

  return (
    <div>
      <h1>Gestión de Vehículos</h1>

      <DataTable
        data={vehiculos}
        columns={vehiculosColumns}
        enablePagination
        pageSize={VEHICULO_TABLE_CONFIG.defaultPageSize}
        emptyMessage="No hay vehículos para mostrar."
        enableGlobalFilter
        enableSorting
        enableColumnFilters
        enableColumnVisibility
        pageSizeOptions={[5, 10, 25, 50, 100]}
        globalFilterValue={globalFilter}
        sortingValue={sorting}
        pageIndexValue={pageIndex}
        pageSizeValue={pageSize}
        onGlobalFilterChange={(value) => {
          setGlobalFilter(value);
          setPageIndex(0);
        }}
        onSortingChange={(nextSorting) => {
          setSorting(nextSorting);
          setPageIndex(0);
        }}
        onPageChange={setPageIndex}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPageIndex(0);
        }}
        onVisibleDataChange={setVisibleRows}
        toolbarActions={toolbarActions}
      />
    </div>
  );
};

export default GestionVehiculosView;
```

## Utilidades Genéricas Disponibles

### `useTableUrlState` Hook

**Ubicación:** `src/hooks/useTableUrlState.ts`

Maneja automáticamente la sincronización del estado de la tabla con los parámetros URL.

**Configuración:**
```typescript
interface UseTableUrlStateConfig {
  defaultPageSize?: number;      // Tamaño de página por defecto (default: 10)
  defaultPageIndex?: number;      // Índice de página inicial (default: 0)
  enableUrlSync?: boolean;        // Habilitar sincronización URL (default: true)
}
```

**Parámetros URL generados:**
- `q` - Filtro global
- `p` - Índice de página (solo si > 0)
- `ps` - Tamaño de página (solo si difiere del default)
- `sort` - Ordenamiento (formato: `columnId:asc|desc`)
- `cf` - Filtros de columna (formato JSON URL-encoded)
- `cv` - Visibilidad de columnas (formato JSON URL-encoded)

**Retorna:**
```typescript
{
  globalFilter: string;
  setGlobalFilter: (value: string) => void;
  sorting: SortingState;
  setSorting: (value: SortingState | ((old: SortingState) => SortingState)) => void;
  pageIndex: number;
  setPageIndex: (value: number) => void;
  pageSize: number;
  setPageSize: (value: number) => void;
  columnFilters: ColumnFiltersState;
  setColumnFilters: (value: ColumnFiltersState | ((old: ColumnFiltersState) => ColumnFiltersState)) => void;
  columnVisibility: VisibilityState;
  setColumnVisibility: (value: VisibilityState | ((old: VisibilityState) => VisibilityState)) => void;
}
```

### `exportToCsv` Utilidad

**Ubicación:** `src/utils/csv.ts`

Exporta datos a CSV con configuración flexible de columnas.

**Uso:**
```typescript
import { exportToCsv, CsvColumn } from "@/utils/csv";

// Definir columnas
const columns: CsvColumn<MyDataType>[] = [
  {
    header: "Nombre",
    accessor: (row) => row.nombre,
  },
  {
    header: "Email",
    accessor: (row) => row.email,
  },
  // Acceso a propiedades anidadas
  {
    header: "Departamento",
    accessor: (row) => row.detalles?.departamento,
  },
];

// Exportar
exportToCsv(data, {
  fileName: "mi_reporte.csv",
  columns: columns,
});
```

**Características:**
- Normalización automática de valores (null, undefined → "")
- Escape de comillas dobles
- Soporte para propiedades anidadas
- Descarga automática del archivo

## Props del DataTable

### Props Requeridas

| Prop | Tipo | Descripción |
|------|------|-------------|
| `data` | `TData[]` | Array de datos a mostrar |
| `columns` | `ColumnDef<TData>[]` | Definición de columnas |

### Props Opcionales

| Prop | Tipo | Default | Descripción |
|------|------|---------|-------------|
| `enablePagination` | `boolean` | `false` | Habilita paginación |
| `pageSize` | `number` | `10` | Tamaño inicial de página |
| `pageSizeOptions` | `number[]` | `[10, 20, 30, 40, 50]` | Opciones de tamaño |
| `enableGlobalFilter` | `boolean` | `false` | Habilita búsqueda global |
| `enableSorting` | `boolean` | `false` | Habilita ordenamiento |
| `enableColumnFilters` | `boolean` | `false` | Habilita filtros por columna |
| `enableColumnVisibility` | `boolean` | `false` | Habilita show/hide columnas |
| `emptyMessage` | `string` | `"No hay datos para mostrar."` | Mensaje cuando no hay datos |
| `toolbarActions` | `React.ReactNode` | `undefined` | Acciones personalizadas |

### Props de Estado Controlado

| Prop | Tipo | Descripción |
|------|------|-------------|
| `globalFilterValue` | `string` | Valor del filtro global |
| `onGlobalFilterChange` | `(value: string) => void` | Callback al cambiar filtro |
| `sortingValue` | `SortingState` | Estado de ordenamiento |
| `onSortingChange` | `(value: SortingState \| Updater<SortingState>) => void` | Callback al ordenar |
| `pageIndexValue` | `number` | Índice de página actual |
| `onPageChange` | `(page: number) => void` | Callback al cambiar página |
| `pageSizeValue` | `number` | Tamaño de página actual |
| `onPageSizeChange` | `(size: number) => void` | Callback al cambiar tamaño |
| `columnVisibilityValue` | `VisibilityState` | Estado de visibilidad |
| `onColumnVisibilityChange` | `(value: VisibilityState \| Updater<VisibilityState>) => void` | Callback al cambiar visibilidad |
| `onVisibleDataChange` | `(rows: TData[]) => void` | Callback con filas visibles (para CSV) |

## Características Adicionales

### Vista Móvil Responsive

La tabla se transforma automáticamente en tarjetas en dispositivos móviles (< 768px):
- Layout de tarjeta vertical
- Todos los datos visibles
- Scroll vertical suave
- No requiere configuración adicional

### Persistencia en URL

Los parámetros de la tabla se sincronizan automáticamente con la URL:
- Permite compartir enlaces con estado específico
- Navegación con botones adelante/atrás funcional
- Estado persiste al recargar página

### Rendimiento

- Usa `useMemo` para memorizar columnas
- Usa `useState` para estado controlado
- Actualización eficiente solo cuando necesario
- Manejo óptimo de re-renders

## Ejemplo Completo de Referencia

Consulta la implementación en:
- **Módulo:** `src/modules/operaciones/actividad/`
- **Vista:** `gestionActividadesView.tsx`
- **Utilidades:** `actividadTable.utils.ts`

## Mejores Prácticas

1. **Siempre usa el hook `useTableUrlState`** para gestión de estado
2. **Define columnas con `useMemo`** para evitar re-renders innecesarios
3. **Configura CSV columns por separado** en el archivo utils
4. **Resetea pageIndex a 0** cuando cambies filtros o ordenamiento
5. **Usa tipos de TypeScript** para todas las props y datos
6. **Implementa `onVisibleDataChange`** si necesitas exportación
7. **Personaliza `toolbarActions`** según necesidades del módulo

## Soporte y Mantenimiento

- **Componente base:** `src/components/common/DataTable.tsx`
- **Tipos:** `src/types/table.ts`
- **Hook URL:** `src/hooks/useTableUrlState.ts`
- **CSV Utility:** `src/utils/csv.ts`

Cualquier mejora o bug debe reportarse y corregirse en estos archivos centrales para beneficiar a todos los módulos.
