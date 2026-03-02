import { ModalOverlayProps } from "../Modal.types";

/**
 * Componente que renderiza el overlay (backdrop) del modal
 * Aplicar un blur backdrop y semi-transparencia para resaltar el modal
 *
 * @param show - Si mostrar el overlay
 * @param closeOutside - Si hacer click cierra el modal
 * @param onClick - Callback cuando se hace click
 * @param className - Clase CSS adicional
 */
export const ModalOverlay = ({
  show,
  closeOutside,
  onClick,
  className,
}: ModalOverlayProps) => {
  if (!show) {
    return null;
  }

  return (
    <div
      className={`fixed inset-0 h-full w-full bg-gray-400/50 backdrop-blur-[32px] ${
        closeOutside ? "cursor-pointer" : ""
      } ${className || ""}`}
      onClick={closeOutside ? onClick : undefined}
      role="presentation"
      aria-hidden="true"
    />
  );
};
