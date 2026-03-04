/**
 * Tipos del componente Modal
 * Centraliza todas las interfaces utilizadas en Modal
 */

/**
 * Props del componente Modal base
 * Define la interfaz pública del componente
 */
export interface ModalProps {
  /** Si el modal está abierto o cerrado */
  isOpen: boolean;

  /** Callback cuando se cierra el modal */
  onClose: () => void;

  /** Clases CSS adicionales para personalizar */
  className?: string;

  /** Contenido del modal */
  children: React.ReactNode;

  /** Si mostrar el botón de cerrar */
  showCloseButton?: boolean;

  /** Si el modal ocupa pantalla completa */
  isFullscreen?: boolean;

  /** Si cerrar cuando se hace click afuera (NO recomendado) */
  closeOutside?: boolean;

  /** Tamaño predefinido del modal */
  size?: "sm" | "md" | "lg" | "xl" | "full";

  /** Animación de entrada */
  animation?: "fade" | "slide" | "zoom" | "none";

  /** Título del modal (opcional, para accesibilidad) */
  title?: string;

  /** Si es un modal importante que no debe cerrarse fácilmente */
  isBlocking?: boolean;

  /** Callback cuando intenta cerrar modal blocking */
  onBlockingAttempt?: () => void;
}

/**
 * Props del overlay (backdrop) del modal
 */
export interface ModalOverlayProps {
  /** Si mostrar el overlay */
  show: boolean;

  /** Si hacer click en overlay cierra el modal */
  closeOutside: boolean;

  /** Callback cuando se hace click en overlay */
  onClick: () => void;

  /** Clase CSS para overlay */
  className?: string;
}

/**
 * Props del header del modal
 */
export interface ModalHeaderProps {
  /** Si mostrar botón de cerrar */
  showCloseButton?: boolean;

  /** Callback cuando se clickea cerrar */
  onClose: () => void;

  /** Clase CSS adicional */
  className?: string;
}

/**
 * Props del contenido del modal
 */
export interface ModalContentProps {
  /** Contenido a renderizar */
  children: React.ReactNode;

  /** Clase CSS adicional */
  className?: string;

  /** Si el contenido es scrolleable */
  scrollable?: boolean;
}

/**
 * Props para acciones del modal (footer)
 */
export interface ModalActionsProps {
  /** Botón primario (aceptar/confirmar) */
  primaryButton?: React.ReactNode;

  /** Botón secundario (cancelar/rechazar) */
  secondaryButton?: React.ReactNode;

  /** Botones adicionales */
  children?: React.ReactNode;

  /** Alinación de botones */
  align?: "left" | "center" | "right";

  /** Clase CSS adicional */
  className?: string;
}

/**
 * Configuración para animaciones del modal
 */
export interface ModalAnimationConfig {
  /** Duración de la animación en ms */
  duration: number;

  /** Tipo de easing */
  easing: "ease-in" | "ease-out" | "ease-in-out" | "linear";
}

/**
 * Map de configuraciones de tamaño
 */
export type SizeConfig = {
  [key in "sm" | "md" | "lg" | "xl" | "full"]: string;
};

/**
 * Map de configuraciones de animación
 */
export type AnimationConfig = {
  [key in "fade" | "slide" | "zoom" | "none"]: string;
};
