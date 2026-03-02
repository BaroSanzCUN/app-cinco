import { ModalActionsProps } from "../Modal.types";

/**
 * Map de alineaciones para los botones
 */
const ALIGNMENT_CLASSES = {
  left: "justify-start",
  center: "justify-center",
  right: "justify-end",
} as const;

/**
 * Componente que renderiza las acciones (botones) del modal
 * Típicamente usado en un footer con botones de confirmar/cancelar
 *
 * @param primaryButton - Botón principal (confirmar)
 * @param secondaryButton - Botón secundario (cancelar)
 * @param children - Botones adicionales
 * @param align - Alineación de los botones
 * @param className - Clase CSS adicional
 */
export const ModalActions = ({
  primaryButton,
  secondaryButton,
  children,
  align = "right",
  className,
}: ModalActionsProps) => {
  const hasActions = primaryButton || secondaryButton || children;

  if (!hasActions) {
    return null;
  }

  const alignmentClass = ALIGNMENT_CLASSES[align as keyof typeof ALIGNMENT_CLASSES];

  return (
    <div
      className={`
        flex items-center gap-3 
        ${alignmentClass}
        ${className || ""}
      `}
    >
      {secondaryButton && <div>{secondaryButton}</div>}
      {primaryButton && <div>{primaryButton}</div>}
      {children && <div>{children}</div>}
    </div>
  );
};
