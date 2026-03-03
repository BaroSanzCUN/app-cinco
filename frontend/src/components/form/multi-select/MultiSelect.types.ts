export interface MultiSelectOption {
  value: string;
  text: string;
}

export interface MultiSelectProps {
  label: string;
  options: MultiSelectOption[];
  defaultSelected?: string[];
  onChange?: (selected: string[]) => void;
  value?: string[];
  disabled?: boolean;
  error?: boolean;
  hint?: string;
}

export interface MultiSelectDropdownProps {
  isOpen: boolean;
  options: MultiSelectOption[];
  selectedOptions: string[];
  onSelect: (optionValue: string) => void;
}

export interface MultiSelectSelectedTagsProps {
  selectedValuesText: string[];
  selectedOptions: string[];
  onRemove: (optionValue: string) => void;
}
