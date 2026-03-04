/**
 * Módulo ModalActividad
 *
 * Modal especializado para crear/editar actividades
 *
 * Estructura modular:
 * - ModalActividad.tsx: Componente principal
 * - ModalActividad.utils.ts: Utilidades y configuración
 * - ModalActividad.hooks.ts: Custom hooks
 * - components/: Sub-componentes especializados
 *
 * @example
 * ```tsx
 * import ModalActividad from './ModalActividad';
 *
 * <ModalActividad
 *   mode="create"
 *   textButton="Nueva Actividad"
 * />
 * ```
 */

export { default } from "./ModalActividad";
export * from "./ModalActividad.hooks";
export * from "./ModalActividad.utils";
