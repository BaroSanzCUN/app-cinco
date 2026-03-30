"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { IAFlowNodeData } from "../types";

const HANDLE_CLASS =
  "h-2.5 w-2.5 rounded-full border border-white/80 bg-sky-400/95 opacity-0 transition-opacity duration-150 group-hover:opacity-100";

const IAFlowNode = ({ data }: NodeProps) => {
  const nodeData = data as IAFlowNodeData;
  const Icon = nodeData.icon;
  const activeClass = nodeData.isActive
    ? "ring-2 ring-lime-300/90 ring-offset-2 ring-offset-slate-900 shadow-[0_0_20px_rgba(132,204,22,.45)]"
    : "";

  return (
    <div className="group relative">
      <Handle
        id="target-left"
        type="target"
        position={Position.Left}
        className={HANDLE_CLASS}
      />
      <Handle
        id="target-top"
        type="target"
        position={Position.Top}
        className={HANDLE_CLASS}
      />
      <Handle
        id="target-right"
        type="target"
        position={Position.Right}
        className={HANDLE_CLASS}
      />
      <Handle
        id="target-bottom"
        type="target"
        position={Position.Bottom}
        className={HANDLE_CLASS}
      />

      <Handle
        id="source-right"
        type="source"
        position={Position.Right}
        className={HANDLE_CLASS}
      />
      <Handle
        id="source-bottom"
        type="source"
        position={Position.Bottom}
        className={HANDLE_CLASS}
      />
      <Handle
        id="source-left"
        type="source"
        position={Position.Left}
        className={HANDLE_CLASS}
      />
      <Handle
        id="source-top"
        type="source"
        position={Position.Top}
        className={HANDLE_CLASS}
      />

      {nodeData.variant === "detached" ? (
        <div className={`w-[65px] bg-transparent px-0 py-1 text-white ${activeClass}`}>
          <div className="space-y-0">
            <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-md border border-sky-300/90 bg-sky-500/95">
              <Icon size={27} />
            </div>
            <p
              className="px-1 text-center text-xs leading-tight font-semibold"
              title={nodeData.title}
            >
              {nodeData.title}
            </p>
            {nodeData.subtitle && (
              <p
                className="px-1 text-center text-[11px] leading-tight text-white/90"
                title={nodeData.subtitle}
              >
                {nodeData.subtitle}
              </p>
            )}
          </div>
        </div>
      ) : (
        <div
          className={`w-[190px] rounded-xl border border-white/20 px-3 py-2 text-white shadow-lg backdrop-blur-sm ${nodeData.tone} ${activeClass}`}
        >
          <div className="grid grid-cols-[36px_1fr] items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-white/25 bg-white/10">
              <Icon size={28} />
            </div>
            <div className="min-w-0 leading-tight">
              <p
                className="truncate text-[11px] font-semibold uppercase tracking-wide text-white/85"
                title={nodeData.title}
              >
                {nodeData.title}
              </p>
              <p
                className="truncate text-xs font-semibold text-white"
                title={nodeData.subtitle || "Accion"}
              >
                {nodeData.subtitle || "Accion"}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IAFlowNode;
