import { ModalContentProps } from "../Modal.types";

/**
 * Componente que renderiza el contenido del modal
 * Maneja scrolling si el contenido es muy largo
 *
 * @param children - Contenido a renderizar
 * @param scrollable - Si el contenido es scrolleable
 * @param className - Clase CSS adicional
 */
export const ModalContent = ({
  children,
  scrollable = false,
  className,
}: ModalContentProps) => {
  return (
    <div
      className={`
        ${scrollable ? "max-h-[70vh] overflow-y-auto" : ""}
        ${className || ""}
      `}
    >
      {children}
    </div>
  );
};
