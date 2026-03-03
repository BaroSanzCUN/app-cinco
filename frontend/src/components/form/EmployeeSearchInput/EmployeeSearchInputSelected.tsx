import Avatar from "@/components/ui/avatar/Avatar";
import { getAvatarUrl } from "@/utils/avatar";
import { Empleado } from "@/types/empleado";

interface EmployeeSearchInputSelectedProps {
  selectedEmployee: Empleado;
  disabled?: boolean;
  onClear: () => void;
}

export const EmployeeSearchInputSelected = ({
  selectedEmployee,
  disabled = false,
  onClear,
}: EmployeeSearchInputSelectedProps) => {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-300 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
      <Avatar
        src={getAvatarUrl(selectedEmployee.link_foto)}
        alt={`${selectedEmployee.nombre} ${selectedEmployee.apellido}`}
        size="medium"
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-gray-900 dark:text-white">
          {selectedEmployee.nombre} {selectedEmployee.apellido} [{" "}
          {selectedEmployee.cedula} ]
        </p>
        <p className="truncate text-xs text-gray-500 dark:text-gray-400">
          {selectedEmployee.cedula} -{" "}
          {selectedEmployee.movil || "1 - SIN ASIGNAR"}
        </p>
      </div>
      {!disabled && (
        <button
          type="button"
          onClick={onClear}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label="Limpiar selección"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
};
