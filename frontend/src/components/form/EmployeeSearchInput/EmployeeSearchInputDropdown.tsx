import Avatar from "@/components/ui/avatar/Avatar";
import { getAvatarUrl } from "@/utils/avatar";
import { Empleado } from "@/types/empleado";
import { EMPLOYEE_SEARCH_CONFIG } from "./EmployeeSearchInput.utils";

interface EmployeeSearchInputDropdownProps {
  isOpen: boolean;
  results: Empleado[];
  searchTerm: string;
  isLoading: boolean;
  onSelect: (employee: Empleado) => void;
}

export const EmployeeSearchInputDropdown = ({
  isOpen,
  results,
  searchTerm,
  isLoading,
  onSelect,
}: EmployeeSearchInputDropdownProps) => {
  if (!isOpen) return null;

  if (results.length > 0) {
    return (
      <div
        className={`absolute z-50 mt-2 w-full overflow-y-auto rounded-lg border border-gray-300 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900 ${EMPLOYEE_SEARCH_CONFIG.maxDropdownHeight}`}
      >
        {results.map((employee) => (
          <button
            key={employee.id}
            type="button"
            onClick={() => onSelect(employee)}
            className="flex w-full items-center gap-3 border-b border-gray-200 p-3 transition-colors last:border-b-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
          >
            <Avatar
              src={getAvatarUrl(employee.link_foto)}
              alt={`${employee.nombre} ${employee.apellido}`}
              size="medium"
            />
            <div className="min-w-0 flex-1 text-left">
              <p className="truncate text-sm font-semibold text-gray-900 dark:text-white">
                {employee.nombre} {employee.apellido} [ {employee.cedula} ]
              </p>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                {employee.cedula} - {employee.cargo || "Sin cargo"}
              </p>
            </div>
          </button>
        ))}
      </div>
    );
  }

  if (
    results.length === 0 &&
    searchTerm.length >= EMPLOYEE_SEARCH_CONFIG.minSearchLength &&
    !isLoading
  ) {
    return (
      <div className="absolute z-50 mt-2 w-full rounded-lg border border-gray-300 bg-white p-4 text-center shadow-lg dark:border-gray-700 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No se encontraron empleados
        </p>
      </div>
    );
  }

  return null;
};
