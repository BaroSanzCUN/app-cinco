import { SizeConfig, AnimationConfig, ModalAnimationConfig } from "./Modal.types";

/**
 * Configuración de tamaños predefinidos para el modal
 * Los tamaños pueden ser personalizados según necesidades
 */
export const MODAL_SIZE_CONFIG: SizeConfig = {
  sm: "max-w-96",      // Small: 384px
  md: "max-w-150",     // Medium: 600px (default)
  lg: "max-w-2xl",     // Large: 672px
  xl: "max-w-4xl",     // Extra Large: 896px
  full: "w-full h-full", // Full screen
};

/**
 * Configuración de animaciones para el modal
 * Usa Tailwind CSS classes
 */
export const MODAL_ANIMATION_CONFIG: AnimationConfig = {
  fade: "animate-fade",
  slide: "animate-slide",
  zoom: "animate-zoom",
  none: "",
};

/**
 * Durations para animaciones (ms)
 */
export const ANIMATION_DURATIONS: Record<string, ModalAnimationConfig> = {
  fast: { duration: 150, easing: "ease-out" },
  normal: { duration: 300, easing: "ease-in-out" },
  slow: { duration: 500, easing: "ease-in" },
};

/**
 * Obtiene la clase de tamaño del modal
 * @param size - Tamaño predefinido o 'md' por defecto
 * @returns Clase de tamaño Tailwind
 */
export const getModalSizeClass = (size: string = "md"): string => {
  return MODAL_SIZE_CONFIG[size as keyof SizeConfig] || MODAL_SIZE_CONFIG.md;
};

/**
 * Obtiene la clase de animación del modal
 * @param animation - Tipo de animación o 'none' por defecto
 * @returns Clase de animación Tailwind
 */
export const getModalAnimationClass = (animation: string = "none"): string => {
  return MODAL_ANIMATION_CONFIG[animation as keyof AnimationConfig] || "";
};

/**
 * Combina clases de tamaño y animación
 * @param size - Tamaño del modal
 * @param animation - Animación del modal
 * @param customClass - Clases adicionales personalizadas
 * @returns String con todas las clases combinadas
 */
export const combineModalClasses = (
  size?: string,
  animation?: string,
  customClass?: string,
): string => {
  const sizeClass = getModalSizeClass(size);
  const animationClass = getModalAnimationClass(animation);
  const baseClass = "relative w-full rounded-3xl bg-white dark:bg-gray-900";

  return [baseClass, sizeClass, animationClass, customClass]
    .filter(Boolean)
    .join(" ");
};

/**
 * Calcula el z-index apropiado para el modal
 * Permite stacking de múltiples modales
 * @param stackLevel - Nivel de apilamiento (0 = fondo)
 * @returns Z-index calculado
 */
export const calculateModalZIndex = (stackLevel: number = 0): number => {
  const baseZIndex = 99999;
  return baseZIndex + stackLevel * 10;
};

/**
 * Maneja el bloqueo de scroll del body
 * Previene scroll mientras el modal está abierto
 * @param block - Si bloquear el scroll
 * @returns Función cleanup
 */
export const toggleBodyScroll = (block: boolean): (() => void) => {
  if (block) {
    document.body.style.overflow = "hidden";
  } else {
    document.body.style.overflow = "unset";
  }

  return () => {
    document.body.style.overflow = "unset";
  };
};

/**
 * Valida si el modal puede cerrarse según su configuración
 * @param isBlocking - Si el modal es bloqueante
 * @param onBlockingAttempt - Callback para intento de cierre
 * @returns true si puede cerrarse, false si no
 */
export const canCloseModal = (
  isBlocking: boolean,
  onBlockingAttempt?: () => void,
): boolean => {
  if (isBlocking) {
    onBlockingAttempt?.();
    return false;
  }
  return true;
};

/**
 * Focaliza un elemento dentro del modal para accesibilidad
 * @param element - Elemento a focalizar
 */
export const focusElement = (element: HTMLElement | null): void => {
  if (element && typeof element.focus === "function") {
    element.focus();
  }
};

/**
 * Genera un ID único para el modal (para accesibilidad)
 * @returns ID único
 */
export const generateModalId = (): string => {
  return `modal-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};
