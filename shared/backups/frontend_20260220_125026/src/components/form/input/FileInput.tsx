import React, { forwardRef, InputHTMLAttributes } from "react";

interface FileInputProps extends InputHTMLAttributes<HTMLInputElement> {
  className?: string;
  hint?: string; // opcional para mensajes
  error?: boolean;
  success?: boolean;
}

// forwardRef para RHF
const FileInput = forwardRef<HTMLInputElement, FileInputProps>(
  ({ className = "", onChange, hint, error = false, success = false, ...props }, ref) => {
    let inputClasses = `focus:border-ring-brand-300 h-8 w-full overflow-hidden rounded-lg border border-gray-300 bg-transparent text-sm text-gray-500 shadow-theme-xs transition-colors file:mr-5 file:border-collapse file:cursor-pointer file:rounded-l-lg file:border-0 file:border-r file:border-solid file:border-gray-200 file:bg-gray-50 file:py-1.5 file:pl-3.5 file:pr-3 file:text-sm file:text-gray-700 placeholder:text-gray-400 hover:file:bg-gray-100 focus:outline-hidden focus:file:ring-brand-300 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:file:border-gray-800 dark:file:bg-white/3 dark:file:text-gray-400 dark:placeholder:text-gray-400 ${className}`;

    if (error) {
      inputClasses += " border-error-500 dark:border-error-500";
    } else if (success) {
      inputClasses += " border-success-500 dark:border-success-500";
    }

    return (
      <div className="relative">
        <input
          type="file"
          className={inputClasses}
          ref={ref}
          onChange={onChange}
          {...props}
        />
        {hint && (
          <p className={`mt-1.5 text-xs ${error ? "text-error-400" : "text-gray-500"}`}>
            {hint}
          </p>
        )}
      </div>
    );
  }
);

FileInput.displayName = "FileInput";

export default FileInput;
