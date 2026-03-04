import { useEffect, useCallback } from "react";
import { toggleBodyScroll, canCloseModal } from "./Modal.utils";

/**
 * Hook para manejar el cierre de un modal cuando se presiona Escape
 * @param isOpen - Si el modal está abierto
 * @param onClose - Callback cuando se presiona Escape
 * @param isBlocking - Si el modal es bloqueante (ignora Escape)
 */
export const useModalEscapeKey = (
  isOpen: boolean,
  onClose: () => void,
  isBlocking: boolean = false,
): void => {
  const handleEscape = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isBlocking) {
        onClose();
      }
    },
    [onClose, isBlocking],
  );

  useEffect(() => {
    if (!isOpen) return;

    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, handleEscape]);
};

/**
 * Hook para manejar el bloqueo de scroll del body mientras el modal está abierto
 * Automáticamente limpia el estado al desmontar
 * @param isOpen - Si el modal está abierto
 */
export const useModalBodyScroll = (isOpen: boolean): void => {
  useEffect(() => {
    if (!isOpen) return;

    // Bloquear scroll
    const cleanup = toggleBodyScroll(true);

    // Limpiar al desmontar o cuando isOpen cambia
    return () => {
      cleanup();
    };
  }, [isOpen]);
};

/**
 * Hook para prevenir el click en el contenido del modal que se propague al overlay
 * Útil para interacciones internas del modal
 * @returns Objeto con manejador de click
 */
export const useModalClickPropagation = () => {
  const handleContentClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Prevenir que el click se propague al overlay
    e.stopPropagation();
  };

  return { handleContentClick };
};

/**
 * Hook para manejar la validación del cierre de modal bloqueante
 * @param isBlocking - Si el modal es bloqueante
 * @param onBlockingAttempt - Callback cuando intenta cerrar modal bloqueante
 * @returns Función para intentar cerrar el modal
 */
export const useModalBlockingClose = (
  isBlocking: boolean,
  onBlockingAttempt?: () => void,
) => {
  const handleClose = useCallback(
    (onClose: () => void): (() => void) => {
      return () => {
        if (canCloseModal(isBlocking, onBlockingAttempt)) {
          onClose();
        }
      };
    },
    [isBlocking, onBlockingAttempt],
  );

  return { handleClose };
};

/**
 * Hook integrado para toda la lógica del modal
 * Combina: Escape key, body scroll, click propagation, blocking close
 * @param isOpen - Si el modal está abierto
 * @param onClose - Callback cuando se cierra
 * @param isBlocking - Si el modal es bloqueante
 * @param onBlockingAttempt - Callback para intento de cierre bloqueado
 */
export const useModalLogic = (
  isOpen: boolean,
  onClose: () => void,
  isBlocking: boolean = false,
  onBlockingAttempt?: () => void,
) => {
  // Escape key
  useModalEscapeKey(isOpen, onClose, isBlocking);

  // Body scroll
  useModalBodyScroll(isOpen);

  // Click propagation
  const { handleContentClick } = useModalClickPropagation();

  // Blocking close
  const { handleClose } = useModalBlockingClose(isBlocking, onBlockingAttempt);

  return {
    handleContentClick,
    handleClose,
  };
};
