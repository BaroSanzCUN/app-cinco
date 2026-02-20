import React, { useState } from "react";

interface Option {
  value: string;
  text: string;
}

interface MultiSelectProps {
  label: string;
  options: Option[];
  defaultSelected?: string[];
  onChange?: (selected: string[]) => void; // Para RHF
  value?: string[]; // Para RHF, opcional
  disabled?: boolean;
  error?: boolean;
  hint?: string;
}

const MultiSelect: React.FC<MultiSelectProps> = ({
  label,
  options,
  defaultSelected = [],
  onChange,
  value,
  disabled = false,
  error = false,
  hint,
}) => {
  // Estado interno solo si no viene `value` (RHF) -> control híbrido
  const [internalSelected, setInternalSelected] = useState<string[]>(
    value ?? defaultSelected
  );
  const [isOpen, setIsOpen] = useState(false);

  const selectedOptions = value ?? internalSelected;

  const toggleDropdown = () => {
    if (disabled) return;
    setIsOpen((prev) => !prev);
  };

  const handleSelect = (optionValue: string) => {
    const newSelected = selectedOptions.includes(optionValue)
      ? selectedOptions.filter((v) => v !== optionValue)
      : [...selectedOptions, optionValue];

    if (value === undefined) setInternalSelected(newSelected); // solo si no viene RHF
    if (onChange) onChange(newSelected); // notificar a RHF
  };

  const removeOption = (optValue: string) => {
    const newSelected = selectedOptions.filter((v) => v !== optValue);
    if (value === undefined) setInternalSelected(newSelected);
    if (onChange) onChange(newSelected);
  };

  const selectedValuesText = selectedOptions.map(
    (v) => options.find((opt) => opt.value === v)?.text || ""
  );

  return (
    <div className="w-full">
      <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400">
        {label}
      </label>

      <div className="relative z-20 inline-block w-full">
        <div className="relative flex flex-col items-center">
          <div onClick={toggleDropdown} className="w-full cursor-pointer">
            <div
              className={`mb-2 flex h-8 rounded-lg border py-0.5 pl-2 pr-3 shadow-theme-xs outline-hidden transition focus:border-brand-300 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-brand-300 ${
                error ? "border-error-500 dark:border-error-500" : "border-gray-300 dark:border-gray-700"
              }`}
            >
              <div className="flex flex-wrap flex-auto gap-2">
                {selectedValuesText.length > 0 ? (
                  selectedValuesText.map((text, index) => (
                    <div
                      key={index}
                      className="group flex items-center justify-center h-6 rounded-full border-[0.7px] border-transparent bg-gray-100 py-1 pl-2.5 pr-2 text-sm text-gray-800 hover:border-gray-200 dark:bg-gray-800 dark:text-white/90 dark:hover:border-gray-800"
                    >
                      <span className="flex-initial max-w-full">{text}</span>
                      <div className="flex flex-row-reverse flex-auto">
                        <div
                          onClick={(e) => {
                            e.stopPropagation();
                            removeOption(selectedOptions[index]);
                          }}
                          className="pl-2 text-gray-500 cursor-pointer group-hover:text-gray-400 dark:text-gray-400"
                        >
                          ×
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <input
                    placeholder="Selecciona opciones"
                    className="w-full h-full p-1 pr-2 text-sm bg-transparent border-0 outline-hidden appearance-none placeholder:text-gray-800 focus:border-0 focus:outline-hidden focus:ring-0 dark:placeholder:text-white/90"
                    readOnly
                    value="Selecciona opciones"
                  />
                )}
              </div>
              <div className="flex items-center py-1 pl-1 pr-1 w-7">
                <button
                  type="button"
                  onClick={toggleDropdown}
                  className="w-5 h-5 text-gray-700 outline-hidden cursor-pointer focus:outline-hidden dark:text-gray-400"
                >
                  <svg
                    className={`stroke-current ${isOpen ? "rotate-180" : ""}`}
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M4.79175 7.39551L10.0001 12.6038L15.2084 7.39551"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {isOpen && (
            <div
              className="absolute left-0 z-40 w-full overflow-y-auto bg-white rounded-lg shadow-sm top-full max-h-select dark:bg-gray-900"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex flex-col">
                {options.map((option) => (
                  <div
                    key={option.value}
                    className={`hover:bg-primary/5 w-full cursor-pointer rounded-t border-b border-gray-200 dark:border-gray-800`}
                    onClick={() => handleSelect(option.value)}
                  >
                    <div
                      className={`relative flex w-full items-center p-2 pl-2 ${
                        selectedOptions.includes(option.value) ? "bg-primary/10" : ""
                      }`}
                    >
                      <div className="mx-2 leading-6 text-gray-800 dark:text-white/90">
                        {option.text}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hint / Error */}
          {hint && (
            <p className={`mt-1.5 text-xs ${error ? "text-error-400" : "text-gray-400 dark:text-gray-400"}`}>
              {hint}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default MultiSelect;
