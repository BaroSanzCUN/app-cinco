import { MultiSelectSelectedTagsProps } from "../MultiSelect.types";

export const MultiSelectSelectedTags = ({
  selectedValuesText,
  selectedOptions,
  onRemove,
}: MultiSelectSelectedTagsProps) => {
  if (selectedValuesText.length === 0) {
    return (
      <input
        placeholder="Selecciona opciones"
        className="h-full w-full appearance-none border-0 bg-transparent p-1 pr-2 text-sm outline-hidden placeholder:text-gray-800 focus:border-0 focus:ring-0 focus:outline-hidden dark:placeholder:text-white/90"
        readOnly
        value="Selecciona opciones"
      />
    );
  }

  return (
    <>
      {selectedValuesText.map((text, index) => (
        <div
          key={`${text}-${index}`}
          className="group flex h-6 items-center justify-center rounded-full border-[0.7px] border-transparent bg-gray-100 py-1 pr-2 pl-2.5 text-sm text-gray-800 hover:border-gray-200 dark:bg-gray-800 dark:text-white/90 dark:hover:border-gray-800"
        >
          <span className="max-w-full flex-initial">{text}</span>
          <div className="flex flex-auto flex-row-reverse">
            <div
              onClick={(event) => {
                event.stopPropagation();
                onRemove(selectedOptions[index]);
              }}
              className="cursor-pointer pl-2 text-gray-500 group-hover:text-gray-400 dark:text-gray-400"
            >
              ×
            </div>
          </div>
        </div>
      ))}
    </>
  );
};
