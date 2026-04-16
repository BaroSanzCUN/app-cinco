import type {
  IADevChartPayload,
  IADevChartSeriesMeta,
} from "@/services/ia-dev.service";
import type { ChartSourcePayload } from "@/modules/programacion/ia-dev/chat/types";

export type SmartChartType =
  | "bar"
  | "horizontal-bar"
  | "grouped-bar"
  | "line"
  | "area"
  | "donut";

export type SmartChartConfig = {
  type: SmartChartType;
  categoryKey: string;
  valueKeys: string[];
  labelKey: string;
  secondaryMetricKey?: string;
  sort: "none" | "asc" | "desc";
  title: string;
  subtitle?: string;
  showLegend: boolean;
  showValues: boolean;
  orientation: "vertical" | "horizontal";
  data: Array<Record<string, unknown>>;
};

const FALLBACK_CATEGORY_KEY = "__category";
const FALLBACK_VALUE_KEY = "__value";

const normalizeNumericString = (value: string): string => {
  let text = value.trim();
  if (!text) return "";
  text = text.replace(/[^\d,.\-]/g, "");
  if (!text || text === "-" || text === "." || text === ",") return "";

  const hasComma = text.includes(",");
  const hasDot = text.includes(".");

  if (hasComma && hasDot) {
    const lastComma = text.lastIndexOf(",");
    const lastDot = text.lastIndexOf(".");
    if (lastComma > lastDot) {
      // Formato tipo 1.234,56 -> 1234.56
      text = text.replace(/\./g, "").replace(",", ".");
    } else {
      // Formato tipo 1,234.56 -> 1234.56
      text = text.replace(/,/g, "");
    }
    return text;
  }

  if (hasComma) {
    // Si termina en ,d o ,dd lo tratamos como decimal.
    if (/,\d{1,2}$/.test(text)) {
      return text.replace(",", ".");
    }
    return text.replace(/,/g, "");
  }

  if (hasDot) {
    const dotCount = (text.match(/\./g) || []).length;
    if (dotCount > 1) {
      const lastDot = text.lastIndexOf(".");
      const intPart = text.slice(0, lastDot).replace(/\./g, "");
      const decimalPart = text.slice(lastDot + 1);
      return `${intPart}.${decimalPart}`;
    }
  }

  return text;
};

const asFiniteNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const normalized = normalizeNumericString(value);
    if (!normalized) return null;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const asLabel = (value: unknown): string => {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  return "";
};

const normalizeRowsFromLabelsSeries = (
  labels: unknown[] | undefined,
  series: unknown[] | undefined,
): Array<Record<string, unknown>> => {
  if (!Array.isArray(labels) || !Array.isArray(series)) return [];
  if (labels.length === 0 || series.length === 0) return [];
  return labels.map((label, index) => ({
    [FALLBACK_CATEGORY_KEY]: asLabel(label) || `categoria_${index + 1}`,
    [FALLBACK_VALUE_KEY]: asFiniteNumber(series[index]) ?? 0,
  }));
};

const normalizeRowsFromTable = (
  table: ChartSourcePayload["table"],
): Array<Record<string, unknown>> => {
  if (!table || !Array.isArray(table.rows) || table.rows.length === 0)
    return [];
  return table.rows.filter((row) => row && typeof row === "object");
};

const normalizeRowsFromChart = (
  chart: IADevChartPayload | null | undefined,
): Array<Record<string, unknown>> => {
  if (!chart) return [];

  if (Array.isArray(chart.data) && chart.data.length > 0) {
    return chart.data.filter((item) => item && typeof item === "object");
  }

  if (Array.isArray(chart.points) && chart.points.length > 0) {
    return chart.points.map((point, index) => ({
      [chart.x_key || FALLBACK_CATEGORY_KEY]:
        point.x || `categoria_${index + 1}`,
      [chart.y_key || FALLBACK_VALUE_KEY]: asFiniteNumber(point.y) ?? 0,
    }));
  }

  if (Array.isArray(chart.labels) && Array.isArray(chart.series)) {
    return normalizeRowsFromLabelsSeries(chart.labels, chart.series);
  }

  return [];
};

const readSeriesValueKeys = (
  chart: IADevChartPayload | null | undefined,
): string[] => {
  if (!chart || !Array.isArray(chart.series)) return [];
  return chart.series
    .map((item) => {
      if (!item || typeof item !== "object") return "";
      const meta = item as IADevChartSeriesMeta;
      return String(meta.value_key || "").trim();
    })
    .filter(Boolean);
};

const pickCategoryKey = (
  rows: Array<Record<string, unknown>>,
  hintedKey?: string,
): string => {
  if (hintedKey && rows.some((row) => asLabel(row[hintedKey]).length > 0)) {
    return hintedKey;
  }

  const candidates = new Map<string, number>();
  for (const row of rows) {
    Object.keys(row).forEach((key) => {
      const label = asLabel(row[key]);
      if (label.length === 0) return;
      candidates.set(key, (candidates.get(key) || 0) + 1);
    });
  }

  return (
    [...candidates.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([key]) => key)
      .find((key) => rows.some((row) => typeof row[key] === "string")) ||
    [...candidates.keys()][0] ||
    FALLBACK_CATEGORY_KEY
  );
};

const pickValueKeys = (
  rows: Array<Record<string, unknown>>,
  categoryKey: string,
  hintedKeys: string[],
): string[] => {
  const numericDensity = new Map<string, number>();

  for (const row of rows) {
    Object.entries(row).forEach(([key, value]) => {
      if (key === categoryKey) return;
      if (asFiniteNumber(value) == null) return;
      numericDensity.set(key, (numericDensity.get(key) || 0) + 1);
    });
  }

  const inferred = [...numericDensity.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key);

  const hinted = hintedKeys.filter((key) => numericDensity.has(key));
  const resolved = [...new Set([...hinted, ...inferred])];
  return resolved.length > 0 ? resolved : [FALLBACK_VALUE_KEY];
};

const isLikelyDateLabel = (label: string): boolean => {
  const normalized = label.trim();
  if (!normalized) return false;
  return (
    /^\d{4}-\d{2}-\d{2}$/.test(normalized) ||
    !Number.isNaN(Date.parse(normalized))
  );
};

const detectTimeSeries = (labels: string[]): boolean => {
  if (labels.length < 3) return false;
  const dateCount = labels.filter((label) => isLikelyDateLabel(label)).length;
  return dateCount / labels.length >= 0.6;
};

const detectPercentageSeries = (
  rows: Array<Record<string, unknown>>,
  valueKey: string,
): boolean => {
  const keyName = valueKey.toLowerCase();
  if (keyName.includes("porcentaje") || keyName.includes("percent"))
    return true;
  const values = rows
    .map((row) => asFiniteNumber(row[valueKey]))
    .filter((value): value is number => value != null);
  if (values.length === 0 || values.length > 8) return false;
  const sum = values.reduce((acc, current) => acc + current, 0);
  const allInRange = values.every((value) => value >= 0 && value <= 100);
  return allInRange && Math.abs(sum - 100) <= 3;
};

const computeLabelStats = (labels: string[]) => {
  if (labels.length === 0) {
    return { avgLength: 0, maxLength: 0 };
  }
  const lengths = labels.map((label) => label.length);
  const total = lengths.reduce((acc, current) => acc + current, 0);
  const maxLength = Math.max(...lengths);
  return {
    avgLength: total / lengths.length,
    maxLength,
  };
};

const hasDominantValue = (
  rows: Array<Record<string, unknown>>,
  valueKey: string,
): boolean => {
  const values = rows
    .map((row) => asFiniteNumber(row[valueKey]))
    .filter((value): value is number => value != null && value >= 0);
  if (values.length < 2) return false;
  const sorted = [...values].sort((a, b) => b - a);
  const total = sorted.reduce((acc, current) => acc + current, 0);
  if (total <= 0) return false;
  const topShare = sorted[0] / total;
  const second = sorted[1] || 1;
  return topShare >= 0.55 || sorted[0] / second >= 3;
};

const buildSubtitleFromMeta = (
  meta: Record<string, unknown>,
): string | undefined => {
  const from = asLabel(meta.periodo_inicio);
  const to = asLabel(meta.periodo_fin);
  if (!from || !to) return undefined;
  return `Periodo: ${from} a ${to}`;
};

const normalizeRowsForConfig = (
  rows: Array<Record<string, unknown>>,
  categoryKey: string,
  valueKeys: string[],
): Array<Record<string, unknown>> => {
  return rows.map((row, index) => {
    const normalized: Record<string, unknown> = {
      [categoryKey]: asLabel(row[categoryKey]) || `categoria_${index + 1}`,
    };
    valueKeys.forEach((key) => {
      normalized[key] = asFiniteNumber(row[key]) ?? 0;
    });
    return normalized;
  });
};

const normalizeChartHint = (rawType: unknown): string => {
  return String(rawType || "")
    .trim()
    .toLowerCase();
};

const getChartInput = (
  payload: ChartSourcePayload,
): {
  rows: Array<Record<string, unknown>>;
  sourceChart: IADevChartPayload | null;
} => {
  const sourceChart = payload.chart || payload.charts?.[0] || null;
  const rowsFromChart = normalizeRowsFromChart(sourceChart);
  if (rowsFromChart.length > 0) return { rows: rowsFromChart, sourceChart };

  const rowsFromTable = normalizeRowsFromTable(payload.table);
  if (rowsFromTable.length > 0) return { rows: rowsFromTable, sourceChart };

  return {
    rows: normalizeRowsFromLabelsSeries(payload.labels, payload.series),
    sourceChart,
  };
};

export const selectBestChartConfig = (
  payload: ChartSourcePayload,
): SmartChartConfig | null => {
  const { rows, sourceChart } = getChartInput(payload);
  if (rows.length === 0) return null;

  const hintedValueKeys = readSeriesValueKeys(sourceChart);
  const categoryKey = pickCategoryKey(rows, sourceChart?.x_key || undefined);
  const valueKeys = pickValueKeys(rows, categoryKey, hintedValueKeys);
  const normalizedRows = normalizeRowsForConfig(rows, categoryKey, valueKeys);

  const labels = normalizedRows.map((row) => asLabel(row[categoryKey]));
  const stats = computeLabelStats(labels);
  const isTimeSeries = detectTimeSeries(labels);
  const primaryValueKey = valueKeys[0];
  const categoriesCount = labels.length;
  const percentageLike = detectPercentageSeries(
    normalizedRows,
    primaryValueKey,
  );
  const dominant = hasDominantValue(normalizedRows, primaryValueKey);

  const chartHint = normalizeChartHint(sourceChart?.type);
  let orientation: "horizontal" | "vertical" = "vertical";
  let type: SmartChartType = "bar";

  if (isTimeSeries) {
    type = chartHint === "area" ? "area" : "line";
  } else if (valueKeys.length > 1) {
    type = "grouped-bar";
  } else if (percentageLike && categoriesCount <= 5) {
    type = chartHint === "pie" ? "donut" : "donut";
  } else {
    type = "bar";
  }

  const shouldUseHorizontalBars =
    !isTimeSeries &&
    type !== "donut" &&
    (stats.maxLength > 12 ||
      stats.avgLength > 8 ||
      categoriesCount > 8 ||
      dominant);

  if (shouldUseHorizontalBars && (type === "bar" || type === "grouped-bar")) {
    orientation = "horizontal";
    if (type === "bar") {
      type = "horizontal-bar";
    }
  }

  const sort: "none" | "asc" | "desc" =
    isTimeSeries || type === "donut" ? "none" : "desc";

  const normalizedType = chartHint;
  if (normalizedType === "line" && !isTimeSeries) {
    type = "line";
  } else if (normalizedType === "area" && !isTimeSeries) {
    type = "area";
  }

  const secondaryMetricKey = valueKeys.find(
    (key) =>
      key !== primaryValueKey &&
      (key.toLowerCase().includes("porcentaje") ||
        key.toLowerCase().includes("percent")),
  );

  const title =
    asLabel(sourceChart?.title) ||
    asLabel((payload.meta || {}).title) ||
    "Analisis de datos";

  const subtitle =
    buildSubtitleFromMeta(payload.meta || {}) ||
    (sourceChart?.meta && typeof sourceChart.meta === "object"
      ? buildSubtitleFromMeta(sourceChart.meta as Record<string, unknown>)
      : undefined);

  return {
    type,
    categoryKey,
    valueKeys,
    labelKey: categoryKey,
    secondaryMetricKey: secondaryMetricKey || undefined,
    sort,
    title,
    subtitle,
    showLegend: valueKeys.length > 1 || type === "donut",
    showValues: type !== "line" && type !== "area",
    orientation,
    data: normalizedRows,
  };
};
