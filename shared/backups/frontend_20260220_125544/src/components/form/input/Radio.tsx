import React, { forwardRef, InputHTMLAttributes } from "react";

interface RadioProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  name: string;
  value: string;
  label: string;
  checked?: boolean;
  disabled?: boolean;
  className?: string;
  error?: boolean; // Para mostrar error si quieres
}

// forwardRef para RHF
const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ id, name, value, label, checked, disabled = false, className = "", onChange, error, ...props }, ref) => {
    return (
      <label
        htmlFor={id}
        className={`relative flex cursor-pointer select-none items-center gap-3 text-sm font-medium ${
          disabled
            ? "text-gray-300 dark:text-gray-600 cursor-not-allowed"
            : error
            ? "text-error-400"
            : "text-gray-700 dark:text-gray-400"
        } ${className}`}
      >
        <input
          id={id}
          name={name}
          type="radio"
          value={value}
          checked={checked}
          disabled={disabled}
          onChange={onChange}
          ref={ref}
          className="sr-only"
          {...props}
        />
        <span
          className={`flex h-5 w-5 items-center justify-center rounded-full border-[1.25px] ${
            checked
              ? "border-brand-500 bg-brand-500"
              : "bg-transparent border-gray-300 dark:border-gray-700"
          } ${
            disabled
              ? "bg-gray-100 dark:bg-gray-700 border-gray-200 dark:border-gray-700"
              : ""
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full bg-white ${checked ? "block" : "hidden"}`}
          ></span>
        </span>
        {label}
      </label>
    );
  }
);

Radio.displayName = "Radio";

export default Radio;
