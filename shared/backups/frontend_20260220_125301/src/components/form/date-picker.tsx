import { useEffect } from 'react';
import flatpickr from 'flatpickr';
import 'flatpickr/dist/flatpickr.css';
import Label from './Label';
import { CalenderIcon } from '../../icons';
import Hook = flatpickr.Options.Hook;
import { DateOption } from 'flatpickr/dist/types/options';

type PropsType = {
  id: string;
  mode?: "single" | "multiple" | "range" | "time";
  onChange?: Hook | Hook[];
  defaultDate?: DateOption;
  label?: string;
  placeholder?: string;
  hint?: string;
  error?: boolean;
  success?: boolean;
  options?: Partial<flatpickr.Options.Options>;
};

export default function DatePicker({
  id,
  mode,
  onChange,
  label,
  defaultDate,
  placeholder,
  hint,
  error,
  success,
  options = {}
}: PropsType) {
  useEffect(() => {
    if (typeof window === "undefined") return;
  
    const flatPickrInstance = flatpickr(`#${id}`, {
      mode: mode || "single",
      // monthSelectorType: "static",
      // dateFormat: "Y-m-d",
      defaultDate,
      onChange,
      disableMobile: false,
      // altInput: true,
      locale: {
        firstDayOfWeek: 1, // Lunes como primer día de la semana
        weekdays: {
          shorthand: ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'],
          longhand: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
        },
        months: {
          shorthand: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
          longhand: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
        },
      },
      appendTo: document.body, // ✅ aquí sí
      ...options,
    });
  
    return () => {
      if (!Array.isArray(flatPickrInstance)) {
        flatPickrInstance.destroy();
      }
    };
  }, [mode, onChange, id, defaultDate, options]);

  return (
    <div>
      {label && <Label htmlFor={id}>{label}</Label>}

      <div className="relative">
        <input
          id={id}
          placeholder={placeholder}
          className={`h-8 w-full rounded-lg border appearance-none px-2 py-0.5 text-sm shadow-theme-xs placeholder:text-gray-400 focus:outline-hidden focus:ring-3  dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30  bg-transparent text-gray-800 border-gray-300 focus:border-brand-300 focus:ring-brand-500/20 dark:border-gray-700  dark:focus:border-brand-800 ${error ? "border-red-400 focus:border-red-400 focus:ring-red-400/20" : ""}`}
          aria-invalid={error ? "true" : "false"}
        />
        {hint && (
          <p
            className={`mt-1.5 text-xs ${error
                ? "text-error-400"
                : success
                  ? "text-success-500"
                  : "text-gray-500"
              }`}
          >
            {hint}
          </p>
        )}

        <span className="absolute text-gray-500 -translate-y-1/2 pointer-events-none right-3 top-1/2 dark:text-gray-400">
          <CalenderIcon className="size-6" />
        </span>
      </div>
    </div>
  );
}
