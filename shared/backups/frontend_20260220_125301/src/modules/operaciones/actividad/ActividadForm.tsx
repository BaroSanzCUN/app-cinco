"use client";

import { useEffect } from "react";
import {
    ActividadSchema,
    ActividadFormData
} from "@/schemas/actividades.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";

import Form from "@/components/form/Form";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import DatePicker from "@/components/form/date-picker";
import TextArea from "@/components/form/input/TextArea";
import Button from "@/components/ui/button/Button";

interface ActividadFormProps {
    defaultValues: ActividadFormData;
    onSubmit: (data: ActividadFormData) => void;
    isLoading?: boolean;
    backendErrors?: Record<string, any> | null;
}

const ActividadForm = ({
    defaultValues,
    onSubmit,
    isLoading,
    backendErrors,
}: ActividadFormProps) => {

    const {
        control,
        handleSubmit,
        reset,
        setError,
        formState: { errors },
    } = useForm<ActividadFormData>({
        resolver: zodResolver(ActividadSchema),
        defaultValues,
    });

    useEffect(() => {
        reset(defaultValues);
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
                    <Label htmlFor="responsable_id">Responsable</Label>
                    <Controller
                        name="responsable_id"
                        control={control}
                        render={({ field }) => (
                            <Input
                                {...field}
                                type="number"
                                id="responsable_id"
                                placeholder="Responsable de la actividad"
                                error={!!errors.responsable_id}
                                hint={errors.responsable_id ? errors.responsable_id.message : undefined}
                                onChange={(e) => field.onChange(e.target.valueAsNumber)}
                                value={field.value ?? ""}
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
                                {...field}
                                id="fecha_fin_estimado"
                                placeholder="Selecciona una fecha"
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
                                {...field}
                                id="fecha_fin_real"
                                placeholder="Selecciona una fecha"
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
