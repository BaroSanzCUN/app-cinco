"use client";

import {
    ActividadSchema,
    ActividadFormData
} from "@/schemas/actividades.schema";
import Form from "@/components/form/Form";
import { useEffect, useState } from "react";
import Label from "@/components/form/Label";
import { Empleado } from "@/types/empleado";
import { preloadAvatar } from "@/utils/avatar";
import Button from "@/components/ui/button/Button";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import Input from "@/components/form/input/InputField";
import DatePicker from "@/components/form/date-picker";
import TextArea from "@/components/form/input/TextArea";
import { getEmpleadoById } from "@/services/empleado.service";
import EmployeeSearchInput from "@/components/form/EmployeeSearchInput";

interface ActividadFormProps {
    defaultValues: ActividadFormData;
    onSubmit: (data: ActividadFormData) => void;
    isLoading?: boolean;
    backendErrors?: Record<string, any> | null;
    mode?: "create" | "edit";
}

const ActividadForm = ({
    defaultValues,
    onSubmit,
    isLoading,
    backendErrors,
    mode = "create",
}: ActividadFormProps) => {

    const [selectedEmployee, setSelectedEmployee] = useState<Empleado | null>(null);

    const {
        control,
        handleSubmit,
        reset,
        setError,
        setValue,
        formState: { errors },
    } = useForm<ActividadFormData>({
        resolver: zodResolver(ActividadSchema),
        defaultValues,
    });

    useEffect(() => {
        let isActive = true;

        reset(defaultValues);
        
        // Si hay un responsable_id en los valores por defecto (modo edición), 
        // crear un objeto Empleado para mostrarlo en el buscador
        if (defaultValues.responsable_id && defaultValues.responsable_id > 0) {
            // Primero, crear un empleado base del snapshot si existe
            let empleadoBase: Empleado | null = null;
            
            if (defaultValues.responsable_snapshot) {
                empleadoBase = {
                    id: defaultValues.responsable_id,
                    cedula: "", // No disponible en el snapshot
                    nombre: defaultValues.responsable_snapshot.nombre.split(" ")[0] || "",
                    apellido: defaultValues.responsable_snapshot.nombre.split(" ").slice(1).join(" ") || "",
                    area: defaultValues.responsable_snapshot.area,
                    carpeta: defaultValues.responsable_snapshot.carpeta,
                    cargo: defaultValues.responsable_snapshot.cargo,
                    movil: defaultValues.responsable_snapshot.movil,
                    estado: "ACTIVO",
                    link_foto: undefined,
                };
                // Mostrar inmediatamente el snapshot
                setSelectedEmployee(empleadoBase);
            }

            // Precargar datos completos del empleado (incluye foto y cédula)
            const preloadEmployee = async () => {
                try {
                    const empleadoFull = await getEmpleadoById(defaultValues.responsable_id);
                    if (!isActive) return;

                    // Combinar datos del snapshot con los datos completos
                    setSelectedEmployee({
                        ...empleadoBase,
                        ...empleadoFull,
                    });

                    // Precargar la foto
                    preloadAvatar(empleadoFull.link_foto);
                } catch (error) {
                    console.error("Error preloading employee:", error);
                    // Si falla, mantener el snapshot que ya fue mostrado
                }
            };

            preloadEmployee();
        } else {
            setSelectedEmployee(null);
        }

        return () => {
            isActive = false;
        };
    }, [defaultValues, reset]);

    useEffect(() => {
        if (backendErrors) {
            Object.keys(backendErrors).forEach((field) => {
                const message = backendErrors[field]?.[0];
    
                if (message) {
                    setError(field as any, {
                        type: "server",
                        message,
                    });
                }
            });
        }
    }, [backendErrors, setError]);

    return (
        <Form 
            handleSubmit={handleSubmit} 
            onSubmit={onSubmit} 
            className="space-y-6"
        >
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 max-h-96 overflow-auto pr-2">

                {/* OT */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="ot">OT</Label>
                    <Controller
                        name="ot"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="ot"
                                placeholder="OT de la actividad"
                                error={!!errors.ot}
                                hint={errors.ot ? errors.ot.message : undefined}
                                disabled={mode === "edit"}
                            />
                        )}
                    />
                </div>

                {/* Fecha de Actividad */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="fecha_inicio_actividad">Fecha de Inicio</Label>
                    <Controller
                        name="fecha_inicio"
                        control={control}
                        render={({ field }) => (
                            <DatePicker
                                id="fecha_actividad"
                                placeholder="Selecciona una fecha"
                                defaultDate={field.value}
                                onChange={(dates: Date[] | Date) => {
                                    const value = Array.isArray(dates) ? dates[0] : dates;
                                    field.onChange(value ? value.toISOString().split("T")[0] : "");
                                }}
                                error={!!errors.fecha_inicio}
                                hint={errors.fecha_inicio ? errors.fecha_inicio.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Responsable */}
                <div className="col-span-2 md:col-span-1">
                    <Controller
                        name="responsable_id"
                        control={control}
                        render={({ field }) => (
                            <EmployeeSearchInput
                                label="Responsable"
                                placeholder="Buscar responsable..."
                                value={selectedEmployee}
                                onChange={(empleado) => {
                                    setSelectedEmployee(empleado);
                                    field.onChange(empleado?.id ?? null);
                                    // También actualizar el snapshot si es necesario
                                    if (empleado) {
                                        setValue("responsable_snapshot", {
                                            nombre: `${empleado.nombre} ${empleado.apellido}`,
                                            area: empleado.area || "",
                                            carpeta: empleado.carpeta || "",
                                            cargo: empleado.cargo || "",
                                            movil: empleado.movil || "",
                                        });
                                    }
                                }}
                                error={!!errors.responsable_id}
                                hint={errors.responsable_id ? String(errors.responsable_id.message) : "Busca por nombre, cédula, cargo o móvil"}
                                name="responsable_id"
                            />
                        )}
                    />
                </div>

                {/* Fecha de Fin Estimada */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="fecha_fin_estimado">Fecha de Fin Estimada</Label>
                    <Controller
                        name="fecha_fin_estimado"
                        control={control}
                        render={({ field }) => (
                            <DatePicker
                                id="fecha_fin_estimado"
                                placeholder="Selecciona una fecha"
                                defaultDate={field.value ? new Date(field.value) : undefined}
                                onChange={(dates: Date[] | Date) => {
                                    const value = Array.isArray(dates) ? dates[0] : dates;
                                    field.onChange(value ? value.toISOString().split("T")[0] : "");
                                }}
                                error={!!errors.fecha_fin_estimado}
                                hint={errors.fecha_fin_estimado ? errors.fecha_fin_estimado.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Fecha de Fin Real */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="fecha_fin_real">Fecha de Fin Real</Label>
                    <Controller
                        name="fecha_fin_real"
                        control={control}
                        render={({ field }) => (
                            <DatePicker
                                id="fecha_fin_real"
                                placeholder="Selecciona una fecha"
                                defaultDate={field.value ? new Date(field.value) : undefined}
                                onChange={(dates: Date[] | Date) => {
                                    const value = Array.isArray(dates) ? dates[0] : dates;
                                    field.onChange(value ? value.toISOString().split("T")[0] : "");
                                }}
                                error={!!errors.fecha_fin_real}
                                hint={errors.fecha_fin_real ? errors.fecha_fin_real.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Tipo de Actividad */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="tipo_actividad">Tipo de Actividad</Label>
                    <Controller
                        name="detalle.tipo_trabajo"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="tipo_actividad"
                                name="detalle.tipo_trabajo"
                                placeholder="Tipo de actividad"
                                error={!!errors.detalle?.tipo_trabajo}
                                hint={errors.detalle?.tipo_trabajo ? errors.detalle.tipo_trabajo.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Descripción */}
                <div className="col-span-2">
                    <Label htmlFor="descripcion">Descripción</Label>
                    <Controller
                        name="detalle.descripcion"
                        control={control}
                        render={({ field }) => (
                            <TextArea
                                {...field}
                                id="descripcion"
                                name="detalle.descripcion"
                                placeholder="Descripción de la actividad"
                                error={!!errors.detalle?.descripcion}
                                hint={errors.detalle?.descripcion ? errors.detalle.descripcion.message : undefined}
                                rows={2}
                            />
                        )}
                    />
                </div>
                
                {/* Ubicación */}
                <div className="col-span-2">
                    <Label htmlFor="ubicacion">Ubicación</Label>
                    <Controller
                        name="ubicacion.direccion"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="ubicacion"
                                name="ubicacion.direccion"
                                placeholder="Dirección de la actividad"
                                error={!!errors.ubicacion?.direccion}
                                hint={errors.ubicacion?.direccion ? errors.ubicacion.direccion.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Coordenada X */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="coordenada_x">Coordenada X</Label>
                    <Controller
                        name="ubicacion.coordenada_x"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="coordenada_x"
                                name="ubicacion.coordenada_x"
                                placeholder="Coordenada X"
                                error={!!errors.ubicacion?.coordenada_x}
                                hint={errors.ubicacion?.coordenada_x ? errors.ubicacion.coordenada_x.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Coordenada Y */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="coordenada_y">Coordenada Y</Label>
                    <Controller
                        name="ubicacion.coordenada_y"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="coordenada_y"
                                name="ubicacion.coordenada_y"
                                placeholder="Coordenada Y"
                                error={!!errors.ubicacion?.coordenada_y}
                                hint={errors.ubicacion?.coordenada_y ? errors.ubicacion.coordenada_y.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Zona */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="zona">Zona</Label>
                    <Controller
                        name="ubicacion.zona"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="zona"
                                name="ubicacion.zona"
                                placeholder="Zona de la actividad"
                                error={!!errors.ubicacion?.zona}
                                hint={errors.ubicacion?.zona ? errors.ubicacion.zona.message : undefined}
                            />
                        )}
                    />
                </div>

                {/* Nodo */}
                <div className="col-span-2 md:col-span-1">
                    <Label htmlFor="nodo">Nodo</Label>
                    <Controller
                        name="ubicacion.nodo"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="text"
                                id="nodo"
                                name="ubicacion.nodo"
                                placeholder="Nodo de la actividad"
                                error={!!errors.ubicacion?.nodo}
                                hint={errors.ubicacion?.nodo ? errors.ubicacion.nodo.message : undefined}
                            />
                        )}
                    />
                </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
                <Button type="submit" size="sm" disabled={isLoading}>
                    Guardar
                </Button>
            </div>
        </Form>
    );
};

export default ActividadForm;
