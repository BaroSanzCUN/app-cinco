"use client";

import { PlusIcon } from "@/icons";
import { useEffect, useState } from "react";
import ModalActividad from "./ModalActividad";
import Alert from "@/components/ui/alert/Alert";
import Badge from "@/components/ui/badge/Badge";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/common/DataTable";
import { useActividadStore } from "@/store/actividad.store";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { ActividadFormData } from "@/schemas/actividades.schema";


const GestionActividadesView = () => {
    const breadcrumbTitles = ["Operaciones", "Gestión de Actividades"];
    const { loadActividades, actividades } = useActividadStore();
    const [showAlert, setShowAlert] = useState(false);

    useEffect(() => {
        loadActividades();
        
        const timer = setTimeout(() => {
            setShowAlert(false);
        }, 5000); // Ocultar alerta después de 5 segundos
        
        return () => clearTimeout(timer);
    }, [loadActividades]);

    const handleEditarActividad = (id: any) => {
        alert(`Editar actividad ${id}`);
    }

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

    const actividadesColumns: ColumnDef<ActividadFormData>[] = [
        {
            header: "ID",
            // accessorKey: "id",
            cell: ({ row }) => {
                const id = row.original.id;

                if (id === undefined) {
                    return null;
                }

                const actividad = {
                    id: id as number,
                    ot: row.original.ot,
                    estado: row.original.estado,
                    // responsable_snapshot: row.original.responsable_snapshot,
                    responsable_id: row.original.responsable_id,
                    fecha_inicio: row.original.fecha_inicio,
                    fecha_fin_estimado: row.original.fecha_fin_estimado,
                    fecha_fin_real: row.original.fecha_fin_real,
                    detalle: row.original.detalle,
                    ubicacion: row.original.ubicacion,
                }

                return (
                    <ModalActividad mode="edit" actividad={actividad} textButton="Editar" />
                );

            }
        },
        {
            header: "OT",
            accessorKey: "ot",
        },
        {
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
                    >{estado}</Badge>
                );
            },
        },
        {
            header: "RESPONSABLE",
            accessorKey: "responsable_snapshot.nombre",
            cell: ({ row }) => {
                const responsable = row.original.responsable_snapshot?.nombre || "Sin responsable";
                return (<span>{responsable}</span>);
            },
        },
    ];

    return (
        <div>
            <PageBreadcrumb pageTitle={breadcrumbTitles} />
            <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-5 py-7 dark:border-gray-800 dark:bg-white/3 xl:px-10 xl:py-12 overflow-auto relative">
                <div className="mx-auto w-full max-w-157.5 text-center">
                    <h3 className="mb-4 font-semibold text-gray-800 text-theme-xl dark:text-white/90 sm:text-2xl">
                        Modulo de Gestión de Actividades
                    </h3>

                    <p className="text-gray-600 dark:text-white/70">
                        Aquí podrás gestionar todas las actividades relacionadas con las operaciones de CINCO SAS.
                    </p>
                </div>
                
                <ModalActividad mode="create" iconButton={<PlusIcon />} textButton="Actividad"  />

                {showAlert &&
                    <Alert
                        variant="success"
                        title="Actividad Creada"
                        message="La actividad ha sido creada exitosamente."
                        // showLink={true}
                        // linkHref="/"
                        // linkText="Learn more"
                    />
                }

                <div className="mt-10">
                    <DataTable
                        data={actividades}
                        columns={actividadesColumns}
                        enablePagination={true}
                        pageSize={6}
                        emptyMessage="No hay actividades para mostrar."
                        enableGlobalFilter={true}
                        enableSorting={true}
                        enableColumnFilters={true}
                        pageSizeOptions={[5, 10, 25, 50, 100]}
                    />
                </div>
            </div>
        </div>
    )

}

export default GestionActividadesView;