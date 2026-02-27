// src/components/form/EmployeeSearchExample.tsx
"use client";

import React, { useState } from "react";
import EmployeeSearchInput from "./EmployeeSearchInput";
import { Empleado } from "@/types/empleado";

/**
 * Componente de ejemplo que muestra cómo usar EmployeeSearchInput
 * en un formulario con múltiples selecciones de empleados
 */
const EmployeeSearchExample: React.FC = () => {
  const [empleado, setEmpleado] = useState<Empleado | null>(null);
  const [supervisor, setSupervisor] = useState<Empleado | null>(null);
  const [jefe, setJefe] = useState<Empleado | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    console.log("Formulario enviado:", {
      empleado,
      supervisor,
      jefe,
    });

    // Aquí puedes hacer lo que necesites con los datos
    alert(
      `Formulario enviado:\n` +
      `Empleado: ${empleado ? `${empleado.nombre} ${empleado.apellido}` : "No seleccionado"}\n` +
      `Supervisor: ${supervisor ? `${supervisor.nombre} ${supervisor.apellido}` : "No seleccionado"}\n` +
      `Jefe: ${jefe ? `${jefe.nombre} ${jefe.apellido}` : "No seleccionado"}`
    );
  };

  const handleReset = () => {
    setEmpleado(null);
    setSupervisor(null);
    setJefe(null);
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Ejemplo de Búsqueda de Empleados
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Campo: Empleado */}
          <EmployeeSearchInput
            label="Empleado"
            placeholder="Buscar empleado por nombre, cédula, cargo o móvil..."
            value={empleado}
            onChange={setEmpleado}
            required
            name="empleado"
            hint="Busca al empleado principal del formulario"
          />

          {/* Campo: Supervisor */}
          <EmployeeSearchInput
            label="Supervisor"
            placeholder="Buscar supervisor..."
            value={supervisor}
            onChange={setSupervisor}
            name="supervisor"
            hint="Selecciona el supervisor directo"
          />

          {/* Campo: Jefe de Área */}
          <EmployeeSearchInput
            label="Jefe de Área"
            placeholder="Buscar jefe de área..."
            value={jefe}
            onChange={setJefe}
            name="jefe"
            hint="Selecciona el jefe del área correspondiente"
          />

          {/* Botones de acción */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              Enviar Formulario
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              Limpiar
            </button>
          </div>
        </form>

        {/* Preview de los valores seleccionados */}
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Valores Seleccionados (Preview):
          </h3>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">Empleado:</span>{" "}
              <span className="text-gray-600 dark:text-gray-400">
                {empleado
                  ? `${empleado.nombre} ${empleado.apellido} (${empleado.cedula})`
                  : "No seleccionado"}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">Supervisor:</span>{" "}
              <span className="text-gray-600 dark:text-gray-400">
                {supervisor
                  ? `${supervisor.nombre} ${supervisor.apellido} (${supervisor.cedula})`
                  : "No seleccionado"}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">Jefe de Área:</span>{" "}
              <span className="text-gray-600 dark:text-gray-400">
                {jefe
                  ? `${jefe.nombre} ${jefe.apellido} (${jefe.cedula})`
                  : "No seleccionado"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Instrucciones de uso */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
          💡 Instrucciones de Uso:
        </h4>
        <ul className="text-sm text-blue-800 dark:text-blue-400 space-y-1 list-disc list-inside">
          <li>Escribe al menos 2 caracteres para iniciar la búsqueda</li>
          <li>Puedes buscar por nombre, apellido, cédula, cargo o móvil</li>
          <li>Los resultados aparecen automáticamente mientras escribes</li>
          <li>Haz clic en un resultado para seleccionarlo</li>
          <li>Usa el botón X para limpiar una selección</li>
        </ul>
      </div>
    </div>
  );
};

export default EmployeeSearchExample;
