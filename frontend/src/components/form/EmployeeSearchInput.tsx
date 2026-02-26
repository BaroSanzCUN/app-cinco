// src/components/form/EmployeeSearchInput.tsx
"use client";

import { Empleado } from "@/types/empleado";
import Avatar from "@/components/ui/avatar/Avatar";
import React, { useState, useEffect, useRef } from "react";
import { getAvatarUrl, preloadAvatars } from "@/utils/avatar";
import { searchEmpleados } from "@/services/empleado.service";

interface EmployeeSearchInputProps {
  label?: string;
  placeholder?: string;
  value?: Empleado | null;
  onChange: (employee: Empleado | null) => void;
  error?: boolean;
  hint?: string;
  disabled?: boolean;
  required?: boolean;
  name?: string;
}

const EmployeeSearchInput: React.FC<EmployeeSearchInputProps> = ({
  label,
  placeholder = "Buscar empleado...",
  value,
  onChange,
  error = false,
  hint,
  disabled = false,
  required = false,
  name,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState<Empleado[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<Empleado | null>(
    value || null
  );
  const wrapperRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Update selected employee when value prop changes
  useEffect(() => {
    setSelectedEmployee(value || null);
  }, [value]);

  // Handle search with debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (searchTerm.length >= 2) {
      setIsLoading(true);
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const data = await searchEmpleados(searchTerm); // Cachea automáticamente
          setResults(data);
          setIsOpen(true);
          
          // Precargar imágenes de los resultados para mejor UX
          const imageUrls = data
            .map((emp) => emp.link_foto)
            .filter(Boolean)
            .map((foto) => getAvatarUrl(foto));
          
          if (imageUrls.length > 0) {
            preloadAvatars(imageUrls);
          }
        } catch (error) {
          console.error("Error searching employees:", error);
          setResults([]);
        } finally {
          setIsLoading(false);
        }
      }, 300);
    } else {
      setResults([]);
      setIsOpen(false);
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchTerm]);

  const handleSelect = (employee: Empleado) => {
    setSelectedEmployee(employee);
    onChange(employee);
    setSearchTerm("");
    setIsOpen(false);
    setResults([]);
  };

  const handleClear = () => {
    setSelectedEmployee(null);
    onChange(null);
    setSearchTerm("");
    setResults([]);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    if (selectedEmployee) {
      setSelectedEmployee(null);
      onChange(null);
    }
  };

  let inputClasses = `h-8 w-full rounded-lg border appearance-none px-2 py-0.5 text-sm shadow-theme-xs placeholder:text-gray-400 focus:outline-hidden focus:ring-3 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30`;

  if (disabled) {
    inputClasses += ` text-gray-500 border-gray-300 cursor-not-allowed dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700`;
  } else if (error) {
    inputClasses += ` text-error-800 border-error-500 focus:ring-3 focus:ring-error-500/10 dark:text-error-400 dark:border-error-500`;
  } else {
    inputClasses += ` bg-transparent text-gray-800 border-gray-300 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800`;
  }

  return (
    <div className="w-full" ref={wrapperRef}>
      {label && (
        <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
          {required && <span className="text-error-500 ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        {/* Selected Employee Display */}
        {selectedEmployee ? (
          <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-300 bg-white dark:bg-gray-900 dark:border-gray-700">
            <Avatar
               
              src={getAvatarUrl(selectedEmployee.link_foto)}
              alt={`${selectedEmployee.nombre} ${selectedEmployee.apellido}`}
              size="medium"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                {selectedEmployee.nombre} {selectedEmployee.apellido} [ {selectedEmployee.cedula} ]
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {selectedEmployee.cedula} - {selectedEmployee.movil || "1 - SIN ASIGNAR"}
              </p>
            </div>
            {!disabled && (
              <button
                type="button"
                onClick={handleClear}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                aria-label="Limpiar selección"
              >
                <svg
                  className="w-5 h-5"
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
        ) : (
          <div className="relative">
            <input
              type="text"
              name={name}
              value={searchTerm}
              onChange={handleInputChange}
              placeholder={placeholder}
              disabled={disabled}
              className={inputClasses}
              autoComplete="off"
            />
            {isLoading && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-500"></div>
              </div>
            )}
          </div>
        )}

        {/* Dropdown Results */}
        {isOpen && results.length > 0 && !selectedEmployee && (
          <div className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg shadow-lg max-h-80 overflow-y-auto">
            {results.map((employee) => (
              <button
                key={employee.id}
                type="button"
                onClick={() => handleSelect(employee)}
                className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors border-b border-gray-200 dark:border-gray-700 last:border-b-0"
              >
                <Avatar
                  src={getAvatarUrl(employee.link_foto)}
                  alt={`${employee.nombre} ${employee.apellido}`}
                  size="medium"
                />
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                    {employee.nombre} {employee.apellido} [ {employee.cedula} ]
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {employee.cedula} - {employee.cargo || "Sin cargo"}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* No Results */}
        {isOpen && results.length === 0 && searchTerm.length >= 2 && !isLoading && (
          <div className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg shadow-lg p-4 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No se encontraron empleados
            </p>
          </div>
        )}
      </div>

      {/* Hint Text */}
      {hint && (
        <p
          className={`mt-1.5 text-xs ${
            error
              ? "text-error-400"
              : "text-gray-500 dark:text-gray-400"
          }`}
        >
          {hint}
        </p>
      )}
    </div>
  );
};

export default EmployeeSearchInput;
