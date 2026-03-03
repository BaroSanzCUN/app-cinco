import { MultiSelectOption } from "./MultiSelect.types";

export const getSelectedValuesText = (
  selectedOptions: string[],
  options: MultiSelectOption[],
): string[] => {
  return selectedOptions.map(
    (value) => options.find((option) => option.value === value)?.text || "",
  );
};
