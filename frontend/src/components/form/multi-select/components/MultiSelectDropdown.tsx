import { MultiSelectDropdownProps } from "../MultiSelect.types";

export const MultiSelectDropdown = ({
  isOpen,
  options,
  selectedOptions,
  onSelect,
}: MultiSelectDropdownProps) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="max-h-select absolute top-full left-0 z-40 w-full overflow-y-auto rounded-lg bg-white shadow-sm dark:bg-gray-900"
      onClick={(event) => event.stopPropagation()}
    >
      <div className="flex flex-col">
        {options.map((option) => (
          <div
            key={option.value}
            className="hover:bg-primary/5 w-full cursor-pointer rounded-t border-b border-gray-200 dark:border-gray-800"
            onClick={() => onSelect(option.value)}
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
  );
};
