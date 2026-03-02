import { ModalHeaderProps } from "../Modal.types";

/**
 * Componente que renderiza el botón de cerrar del modal
 * Ubicado en la esquina superior derecha
 *
 * @param showCloseButton - Si mostrar el botón
 * @param onClose - Callback cuando se clickea cerrar
 * @param className - Clase CSS adicional
 */
export const ModalCloseButton = ({
  showCloseButton = true,
  onClose,
  className,
}: Pick<ModalHeaderProps, "showCloseButton" | "onClose" | "className">) => {
  if (!showCloseButton) {
    return null;
  }

  return (
    <button
      onClick={onClose}
      className={`absolute top-3 right-3 z-999 flex h-9.5 w-9.5 items-center justify-center rounded-full bg-gray-100 text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-700 sm:top-6 sm:right-6 sm:h-11 sm:w-11 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white ${className || ""}`}
      aria-label="Cerrar modal"
      type="button"
    >
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M6.04289 16.5413C5.65237 16.9318 5.65237 17.565 6.04289 17.9555C6.43342 18.346 7.06658 18.346 7.45711 17.9555L11.9987 13.4139L16.5408 17.956C16.9313 18.3466 17.5645 18.3466 17.955 17.956C18.3455 17.5655 18.3455 16.9323 17.955 16.5418L13.4129 11.9997L17.955 7.4576C18.3455 7.06707 18.3455 6.43391 17.955 6.04338C17.5645 5.65286 16.9313 5.65286 16.5408 6.04338L11.9987 10.5855L7.45711 6.0439C7.06658 5.65338 6.43342 5.65338 6.04289 6.0439C5.65237 6.43442 5.65237 7.06759 6.04289 7.45811L10.5845 11.9997L6.04289 16.5413Z"
          fill="currentColor"
        />
      </svg>
    </button>
  );
};

/**
 * Componente del header del modal
 * Incluye el botón de cerrar
 *
 * @param showCloseButton - Si mostrar botón de cerrar
 * @param onClose - Callback cuando se cierra
 * @param className - Clase CSS adicional
 */
export const ModalHeader = ({
  showCloseButton = true,
  onClose,
  className,
}: ModalHeaderProps) => {
  return (
    <div className={`relative ${className || ""}`}>
      <ModalCloseButton
        showCloseButton={showCloseButton}
        onClose={onClose}
      />
    </div>
  );
};
