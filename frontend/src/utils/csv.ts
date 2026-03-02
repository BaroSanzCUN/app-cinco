export interface CsvColumn<TData = any> {
  header: string;
  accessor: (row: TData) => unknown;
}

export interface CsvExportConfig<TData = any> {
  fileName?: string;
  columns: CsvColumn<TData>[];
}

const normalizeCsvValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).replace(/"/g, '""');
};

export const exportToCsv = <TData,>(
  rows: TData[],
  config: CsvExportConfig<TData>,
): void => {
  const fileName = config.fileName ?? "export.csv";
  const headers = config.columns.map((col) => col.header);

  const csvRows = rows.map((row) =>
    config.columns.map((col) => normalizeCsvValue(col.accessor(row))),
  );

  const csvContent = [headers, ...csvRows]
    .map((columns) => columns.map((column) => `"${column}"`).join(","))
    .join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = fileName;
  anchor.style.display = "none";

  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  URL.revokeObjectURL(url);
};
