import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  ActividadSchema,
  ActividadFormData,
} from "@/schemas/actividades.schema";
import { Empleado } from "@/types/empleado";
import { getEmpleadoById } from "@/services/empleado.service";
import { preloadAvatar } from "@/utils/avatar";
import {
  buildResponsableSnapshot,
  getSnapshotEmpleado,
} from "./ActividadForm.utils";

interface UseActividadFormLogicParams {
  defaultValues: ActividadFormData;
  backendErrors?: Record<string, any> | null;
}

export const useActividadFormLogic = ({
  defaultValues,
  backendErrors,
}: UseActividadFormLogicParams) => {
  const [selectedEmployee, setSelectedEmployee] = useState<Empleado | null>(
    null,
  );

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

    const loadEmployee = async () => {
      if (defaultValues.responsable_id && defaultValues.responsable_id > 0) {
        try {
          const empleadoBase = getSnapshotEmpleado(defaultValues);

          if (empleadoBase && isActive) {
            setSelectedEmployee(empleadoBase);
          }

          const empleadoFull = await getEmpleadoById(
            defaultValues.responsable_id,
          );
          if (!isActive) return;

          setSelectedEmployee({
            ...empleadoBase,
            ...empleadoFull,
          });

          preloadAvatar(empleadoFull.link_foto);
        } catch (error) {
          console.error("Error preloading employee:", error);
        }
      } else if (isActive) {
        setSelectedEmployee(null);
      }
    };

    loadEmployee();

    return () => {
      isActive = false;
    };
  }, [defaultValues, reset]);

  useEffect(() => {
    if (!backendErrors) return;

    Object.keys(backendErrors).forEach((field) => {
      const message = backendErrors[field]?.[0];

      if (message) {
        setError(field as any, {
          type: "server",
          message,
        });
      }
    });
  }, [backendErrors, setError]);

  const handleEmployeeChange = (empleado: Empleado | null) => {
    setSelectedEmployee(empleado);
    setValue("responsable_id", empleado?.id ?? 0);

    if (empleado) {
      setValue("responsable_snapshot", buildResponsableSnapshot(empleado));
    }
  };

  return {
    control,
    errors,
    handleSubmit,
    selectedEmployee,
    handleEmployeeChange,
  };
};
