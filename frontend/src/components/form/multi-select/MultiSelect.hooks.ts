import { useState } from "react";

interface UseMultiSelectStateParams {
  defaultSelected: string[];
  value?: string[];
  onChange?: (selected: string[]) => void;
  disabled?: boolean;
}

export const useMultiSelectState = ({
  defaultSelected,
  value,
  onChange,
  disabled = false,
}: UseMultiSelectStateParams) => {
  const [internalSelected, setInternalSelected] = useState<string[]>(
    value ?? defaultSelected,
  );
  const [isOpen, setIsOpen] = useState(false);

  const selectedOptions = value ?? internalSelected;

  const toggleDropdown = () => {
    if (disabled) return;
    setIsOpen((prev) => !prev);
  };

  const updateSelection = (newSelected: string[]) => {
    if (value === undefined) {
      setInternalSelected(newSelected);
    }

    if (onChange) {
      onChange(newSelected);
    }
  };

  const handleSelect = (optionValue: string) => {
    const newSelected = selectedOptions.includes(optionValue)
      ? selectedOptions.filter((valueItem) => valueItem !== optionValue)
      : [...selectedOptions, optionValue];

    updateSelection(newSelected);
  };

  const removeOption = (optionValue: string) => {
    const newSelected = selectedOptions.filter(
      (valueItem) => valueItem !== optionValue,
    );
    updateSelection(newSelected);
  };

  return {
    isOpen,
    selectedOptions,
    toggleDropdown,
    handleSelect,
    removeOption,
  };
};
