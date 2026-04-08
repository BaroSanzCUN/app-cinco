"use client";

import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from "@xyflow/react";

const IAFlowEdge = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 18,
    offset: 28,
  });

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: "#e2e8f0",
          strokeWidth: 2,
          opacity: 0.95,
        }}
      />
      {typeof data?.label === "string" && data.label.trim() ? (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute rounded-md border border-slate-500/70 bg-slate-900/90 px-1.5 py-0.5 text-[10px] font-semibold text-white"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
};

export default IAFlowEdge;
