"use client";

import { PlusIcon } from "@/icons";
import { useEffect, useMemo, useState } from "react";
import ModalActividad from "./ModalActividad";
import Alert from "@/components/ui/alert/Alert";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/common/DataTable";
import { useActividadStore } from "@/store/actividad.store";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { ActividadFormData } from "@/schemas/actividades.schema";
import { DownloadIcon } from "@/icons";
import {
  actividadCsvColumns,
  ACTIVIDAD_TABLE_CONFIG,
} from "./actividadTable.utils";
import { useTableUrlState } from "@/hooks/useTableUrlState";
import { exportToCsv } from "@/utils/csv";

const GestionActividadesView = () => {
  const breadcrumbTitles = ["Operaciones", "Gestión de Actividades"];
  const { loadActividades, actividades } = useActividadStore();
  const [showAlert, setShowAlert] = useState(false);
  const [visibleRows, setVisibleRows] = useState<ActividadFormData[]>([]);

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
    defaultPageSize: ACTIVIDAD_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: ACTIVIDAD_TABLE_CONFIG.defaultPageIndex,
  });

  useEffect(() => {
    loadActividades();

    const timer = setTimeout(() => {
      setShowAlert(false);
    }, 5000);

    return () => clearTimeout(timer);
  }, [loadActividades]);

  // {
  //     "id": 3,
  //     "detalle": {
  //         "id": 3,
  //         "tipo_trabajo": "PRUEBA",
  //         "descripcion": "Esta es una actividad de prueba",
  //         "extra": null
  //     },
  //     "ubicacion": {
  //         "id": 3,
  //         "direccion": "Medellin",
  //         "coordenada_x": "000000000",
  //         "coordenada_y": "000000000",
  //         "zona": "SUR",
  //         "nodo": "N600"
  //     },
  //     "responsable_snapshot": {
  //         "nombre": "CARLOS ALBERTO",
  //         "area": "DEPARTAMENTO TI",
  //         "carpeta": "PROGRAMACION",
  //         "cargo": "LIDER DESARROLLADOR",
  //         "movil": "PROGRAM01"
  //     },
  //     "ot": "00003",
  //     "estado": "pendiente",
  //     "responsable_id": 2761,
  //     "fecha_inicio": "2026-02-17",
  //     "fecha_fin_estimado": "2026-02-19",
  //     "fecha_fin_real": "1900-01-01",
  //     "created_at": "2026-02-12T16:01:35.352362-05:00",
  //     "created_by": null,
  //     "updated_at": "2026-02-12T16:01:35.352362-05:00",
  //     "updated_by": null,
  //     "is_deleted": false,
  //     "deleted_at": null,
  //     "deleted_by": null
  // },

  const actividadesColumns: ColumnDef<ActividadFormData>[] = useMemo(
    () => [
      {
        id: "acciones",
        header: "ACCIONES",
        enableSorting: false,
        enableColumnFilter: false,
        enableHiding: false,
        cell: ({ row }) => {
          const id = row.original.id;

          if (id === undefined) {
            return null;
          }

          const actividad = {
            id: id as number,
            ot: row.original.ot,
            estado: row.original.estado,
            responsable_snapshot: row.original.responsable_snapshot,
            responsable_id: row.original.responsable_id,
            fecha_inicio: row.original.fecha_inicio,
            fecha_fin_estimado: row.original.fecha_fin_estimado,
            fecha_fin_real: row.original.fecha_fin_real,
            detalle: row.original.detalle,
            ubicacion: row.original.ubicacion,
          };

          return (
            <ModalActividad
              mode="edit"
              actividad={actividad}
              textButton="Editar"
            />
          );
        },
      },
      {
        id: "id",
        header: "ID",
        accessorKey: "id",
      },
      {
        id: "ot",
        header: "OT",
        accessorKey: "ot",
      },
      {
        id: "estado",
        header: "ESTADO",
        accessorKey: "estado",
        cell: ({ row }) => {
          const estado = row.original.estado || "Sin estado";
          return (
            <Badge
              size="sm"
              color={
                estado == "completada"
                  ? "success"
                  : estado == "pendiente"
                    ? "warning"
                    : "error"
              }
            >
              {estado}
            </Badge>
          );
        },
      },
      {
        id: "responsable",
        header: "RESPONSABLE",
        accessorKey: "responsable_snapshot.nombre",
        cell: ({ row }) => {
          const responsable =
            row.original.responsable_snapshot?.nombre || "Sin responsable";
          return <span>{responsable}</span>;
        },
      },
    ],
    [],
  );

  const handleExportCsv = () => {
    if (!visibleRows.length) {
      return;
    }

    exportToCsv(visibleRows, {
      fileName: ACTIVIDAD_TABLE_CONFIG.csvFileName,
      columns: actividadCsvColumns,
    });
  };

  const toolbarActions = (
    <Button
      variant="outline"
      size="sm"
      onClick={handleExportCsv}
      startIcon={<DownloadIcon className="h-4 w-4" />}
      disabled={!visibleRows.length}
    >
      Exportar CSV
    </Button>
  );

  return (
    <div>
      <PageBreadcrumb pageTitle={breadcrumbTitles} />
      <div className="relative min-h-screen overflow-auto rounded-2xl border border-gray-200 bg-white px-5 py-7 xl:px-10 xl:py-12 dark:border-gray-800 dark:bg-white/3">
        <div className="mx-auto w-full max-w-157.5 text-center">
          <h3 className="text-theme-xl mb-4 font-semibold text-gray-800 sm:text-2xl dark:text-white/90">
            Modulo de Gestión de Actividades
          </h3>

          <p className="text-gray-600 dark:text-white/70">
            Aquí podrás gestionar todas las actividades relacionadas con las
            operaciones de CINCO SAS.
          </p>
        </div>

        <ModalActividad
          mode="create"
          iconButton={<PlusIcon />}
          textButton="Actividad"
        />

        {showAlert && (
          <Alert
            variant="success"
            title="Actividad Creada"
            message="La actividad ha sido creada exitosamente."
            // showLink={true}
            // linkHref="/"
            // linkText="Learn more"
          />
        )}

        <div className="mt-10">
          <DataTable
            data={actividades}
            columns={actividadesColumns}
            enablePagination
            pageSize={ACTIVIDAD_TABLE_CONFIG.defaultPageSize}
            emptyMessage="No hay actividades para mostrar."
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
      </div>
    </div>
  );
};

export default GestionActividadesView;
