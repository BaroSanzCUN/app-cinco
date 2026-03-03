import { ColumnDef } from "@tanstack/react-table";
import { ActividadFormData } from "@/schemas/actividades.schema";
import Badge from "@/components/ui/badge/Badge";
import ModalActividad from "./ModalActividad";
import {
  actividadCsvColumns,
  ACTIVIDAD_TABLE_CONFIG,
} from "./actividadTable.utils";
import { exportToCsv } from "@/utils/csv";

export const getActividadesColumns = (): ColumnDef<ActividadFormData>[] => [
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
        <ModalActividad mode="edit" actividad={actividad} textButton="Editar" />
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
];

export const handleExportToCsvHelper = (visibleRows: ActividadFormData[]) => {
  if (!visibleRows.length) {
    return;
  }

  exportToCsv(visibleRows, {
    fileName: ACTIVIDAD_TABLE_CONFIG.csvFileName,
    columns: actividadCsvColumns,
  });
};

export const GESTION_ACTIVIDADES_CONFIG = {
  breadcrumbTitles: ["Operaciones", "Gestión de Actividades"],
  title: "Modulo de Gestión de Actividades",
  description:
    "Aquí podrás gestionar todas las actividades relacionadas con las operaciones de CINCO SAS.",
  alertDuration: 5000,
  pageSizeOptions: [5, 10, 25, 50, 100],
} as const;
