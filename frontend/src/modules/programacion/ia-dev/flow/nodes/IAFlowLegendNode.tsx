"use client";

import type { NodeProps } from "@xyflow/react";
import type { IAFlowLegendNodeData } from "../types";

const IAFlowLegendNode = ({ data }: NodeProps) => {
  const legend = data as IAFlowLegendNodeData;

  return (
    <div className="min-w-[140px] rounded-lg border border-slate-700/70 bg-slate-950/75 px-2 py-2 text-slate-200 shadow-lg backdrop-blur-sm">
      <p className="mb-2 text-[10px] font-semibold tracking-wide text-slate-400 uppercase">
        {legend.title}
      </p>
      <div className={`flex ${legend.mode === "areas" ? "flex-col" : "flex-wrap"} gap-1`}>
        {legend.items.map((item) => {
          const active = legend.activeItem === item;
          return (
            <span
              key={item}
              className={`truncate rounded-md border px-2 py-1 text-[10px] font-semibold ${
                active
                  ? "border-lime-400/70 bg-lime-400/15 text-lime-200"
                  : "border-slate-700 bg-slate-900/70 text-slate-300"
              }`}
              title={item}
            >
              {item}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export default IAFlowLegendNode;
