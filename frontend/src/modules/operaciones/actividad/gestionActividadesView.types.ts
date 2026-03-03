import { SortingState, ColumnDef } from "@tanstack/react-table";
import { ActividadFormData } from "@/schemas/actividades.schema";

export interface GestionActividadesTableState {
  globalFilter: string;
  sorting: SortingState;
  pageIndex: number;
  pageSize: number;
  visibleRows: ActividadFormData[];
  columns: ColumnDef<ActividadFormData>[];
}

export interface GestionActividadesTableActions {
  setGlobalFilter: (value: string) => void;
  setSorting: (sorting: SortingState) => void;
  setPageIndex: (index: number) => void;
  setPageSize: (size: number) => void;
  setVisibleRows: (rows: ActividadFormData[]) => void;
}

export interface GestionActividadesTableProps
  extends GestionActividadesTableState, GestionActividadesTableActions {
  actividades: ActividadFormData[];
}
