"use client";

import { useModal } from "@/hooks/useModal";
import { Modal } from "@/components/ui/modal";
import Button from "@/components/ui/button/Button";
import { Actividad } from "../types";
import {
  getDefaultValues,
  getModalTitle,
  MODAL_ACTIVIDAD_CONFIG,
} from "./ModalActividad.utils";
import { useModalActividadLogic } from "./ModalActividad.hooks";
import { ActividadFormContainer } from "./components/ActividadFormContainer";

interface ModalActividadProps {
  /** Modo: crear o editar */
  mode: "create" | "edit";

  /** Datos de actividad (solo requerido en modo edit) */
  actividad?: Actividad;

  /** Texto del botón que abre el modal */
  textButton?: string;

  /** Ícono del botón que abre el modal */
  iconButton?: React.ReactNode;
}

/**
 * Modal para crear/editar actividades
 *
 * Características:
 * - Apertura/cierre del modal automático
 * - Validación de formulario
 * - Manejo de errores
 * - Estados de carga
 *
 * @example
 * ```tsx
 * <ModalActividad
 *   mode="create"
 *   textButton="Nueva Actividad"
 *   iconButton={<PlusIcon />}
 * />
 *
 * <ModalActividad
 *   mode="edit"
 *   actividad={actividad}
 *   textButton="Editar"
 * />
 * ```
 */
const ModalActividad = ({
  mode,
  actividad,
  textButton,
  iconButton,
}: ModalActividadProps) => {
  // Hook para controlar apertura/cierre del modal
  const { isOpen, openModal, closeModal } = useModal();

  // Lógica integrada del modal
  const { handleSubmit, isLoading, error } = useModalActividadLogic(
    mode,
    actividad,
    closeModal,
  );

  // Valores por defecto del formulario
  const defaultValues = getDefaultValues(mode, actividad);

  // Título del modal según modo
  const modalTitle = getModalTitle(mode);

  return (
    <>
      {/* Botón que abre el modal */}
      <Button onClick={openModal} startIcon={iconButton}>
        {textButton}
      </Button>

      {/* Modal */}
      <Modal
        isOpen={isOpen}
        onClose={closeModal}
        size="md"
        className={`${MODAL_ACTIVIDAD_CONFIG.maxWidth} ${MODAL_ACTIVIDAD_CONFIG.padding}`}
      >
        {/* Header */}
        <Modal.Header showCloseButton onClose={closeModal} />

        {/* Contenido */}
        <Modal.Content scrollable={MODAL_ACTIVIDAD_CONFIG.scrollable}>
          {/* Título */}
          <div className="mb-6 text-lg font-medium">{modalTitle}</div>

          {/* Formulario */}
          <ActividadFormContainer
            mode={mode}
            defaultValues={defaultValues}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            backendErrors={error}
          />
        </Modal.Content>
      </Modal>
    </>
  );
};

export default ModalActividad;
