import React from "react";
import { MultiSelectProps } from "./MultiSelect.types";
import { useMultiSelectState } from "./MultiSelect.hooks";
import { getSelectedValuesText } from "./MultiSelect.utils";
import { MultiSelectSelectedTags } from "./components/MultiSelectSelectedTags";
import { MultiSelectDropdown } from "./components/MultiSelectDropdown";

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
  const {
    isOpen,
    selectedOptions,
    toggleDropdown,
    handleSelect,
    removeOption,
  } = useMultiSelectState({
    defaultSelected,
    value,
    onChange,
    disabled,
  });

  const selectedValuesText = getSelectedValuesText(selectedOptions, options);

  return (
    <div className="w-full">
      <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400">
        {label}
      </label>

      <div className="relative z-20 inline-block w-full">
        <div className="relative flex flex-col items-center">
          <div onClick={toggleDropdown} className="w-full cursor-pointer">
            <div
              className={`shadow-theme-xs focus:border-brand-300 dark:focus:border-brand-300 mb-2 flex h-8 rounded-lg border py-0.5 pr-3 pl-2 outline-hidden transition dark:border-gray-700 dark:bg-gray-900 ${
                error
                  ? "border-error-500 dark:border-error-500"
                  : "border-gray-300 dark:border-gray-700"
              }`}
            >
              <div className="flex flex-auto flex-wrap gap-2">
                <MultiSelectSelectedTags
                  selectedValuesText={selectedValuesText}
                  selectedOptions={selectedOptions}
                  onRemove={removeOption}
                />
              </div>
              <div className="flex w-7 items-center py-1 pr-1 pl-1">
                <button
                  type="button"
                  onClick={toggleDropdown}
                  className="h-5 w-5 cursor-pointer text-gray-700 outline-hidden focus:outline-hidden dark:text-gray-400"
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

          <MultiSelectDropdown
            isOpen={isOpen}
            options={options}
            selectedOptions={selectedOptions}
            onSelect={handleSelect}
          />

          {hint && (
            <p
              className={`mt-1.5 text-xs ${error ? "text-error-400" : "text-gray-400 dark:text-gray-400"}`}
            >
              {hint}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default MultiSelect;
