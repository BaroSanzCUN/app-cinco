"use client";

import { BarChart2 } from "lucide-react";
import type { NormalizedKPI } from "@/modules/programacion/ia-dev/chat/types";

type KPISectionProps = {
  items: NormalizedKPI[];
};

const formatValue = (value: number | string) => {
  if (typeof value !== "number" || !Number.isFinite(value))
    return String(value);
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 }).format(
    value,
  );
};

const KPISection = ({ items }: KPISectionProps) => {
  if (items.length === 0) return null;

  return (
    <section className="space-y-2">
      <p className="text-[11px] font-semibold tracking-wide text-gray-500 uppercase dark:text-gray-400">
        KPIs
      </p>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((kpi) => (
          <article
            key={kpi.key}
            className="shadow-theme-xs rounded-xl border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-900/80"
          >
            <div className="mb-1 flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
              <BarChart2 size={12} />
              <span className="truncate">{kpi.label}</span>
            </div>
            <p className="truncate text-lg font-semibold text-gray-900 dark:text-white">
              {formatValue(kpi.value)}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
};

export default KPISection;
