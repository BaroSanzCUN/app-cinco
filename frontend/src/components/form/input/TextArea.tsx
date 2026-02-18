import React, { forwardRef, TextareaHTMLAttributes } from "react";

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean; // Error state for styling
  hint?: string;   // Hint text
  success?: boolean; // Optional success state
}

// forwardRef para RHF
const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  (
    {
      placeholder = "Enter your message",
      rows = 3,
      value,
      defaultValue,
      onChange,
      disabled = false,
      error = false,
      success = false,
      className = "",
      hint,
      ...props
    },
    ref
  ) => {
    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      if (onChange) onChange(e);
    };

    let textareaClasses = `w-full rounded-lg border px-2 py-0.5 text-sm shadow-theme-xs focus:outline-hidden ${className}`;

    if (disabled) {
      textareaClasses += ` bg-gray-100 opacity-50 text-gray-500 border-gray-300 cursor-not-allowed dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700`;
    } else if (error) {
      textareaClasses += ` bg-transparent text-gray-400 border-error-500 focus:border-error-300 focus:ring-3 focus:ring-error-500/10 dark:border-error-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-error-800`;
    } else if (success) {
      textareaClasses += ` text-success-500 border-success-400 focus:ring-success-500/10 focus:border-success-300 dark:text-success-400 dark:border-success-500`;
    } else {
      textareaClasses += ` bg-transparent text-gray-400 border-gray-300 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800`;
    }

    return (
      <div className="relative">
        <textarea
          ref={ref}
          placeholder={placeholder}
          rows={rows}
          value={value ?? ""}
          defaultValue={defaultValue}
          onChange={handleChange}
          disabled={disabled}
          className={textareaClasses}
          aria-invalid={error ? "true" : "false"}
          {...props}
        />
        {hint && (
          <p
            className={`text-xs ${
              error
                ? "text-error-400"
                : success
                  ? "text-success-400"
                  : "text-gray-500"
            }`}
          >
            {hint}
          </p>
        )}
      </div>
    );
  }
);

TextArea.displayName = "TextArea";

export default TextArea;
