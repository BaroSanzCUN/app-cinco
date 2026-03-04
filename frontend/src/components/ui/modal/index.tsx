/**
 * Módulo Modal
 *
 * Componente reutilizable de modal con arquitectura modular.
 *
 * Estructura:
 * - Modal.tsx: Componente principal (orquestador)
 * - Modal.hooks.ts: Custom hooks para lógica del modal
 * - Modal.utils.ts: Funciones helper y configuraciones
 * - Modal.types.ts: Tipos TypeScript
 * - components/: Sub-componentes especializados
 *
 * Características:
 * - Escape key para cerrar
 * - Bloqueo de scroll del body
 * - Modales bloqueantes
 * - Tamaños predefinidos
 * - Animaciones personalizables
 * - Accesibilidad mejorada
 * - Forward ref soporte
 * - Sub-componentes disponibles como Modal.Header, Modal.Content, etc
 *
 * @example
 * ```tsx
 * import { Modal } from '@/components/ui/modal';
 *
 * <Modal isOpen onClose={() => {}}>
 *   <Modal.Header showCloseButton />
 *   <Modal.Content>Contenido</Modal.Content>
 *   <Modal.Actions primaryButton={<Button>OK</Button>} />
 * </Modal>
 * ```
 */

export { Modal } from "./Modal";
export type { ModalProps } from "./Modal.types";
export {
  ModalOverlay,
  ModalHeader,
  ModalCloseButton,
  ModalContent,
  ModalActions,
} from "./components";
