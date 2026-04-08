import type { LucideIcon } from "lucide-react";
import type { Node } from "@xyflow/react";

export type IAFlowNodeVariant = "detached" | "split";

export type IAFlowTreeNode = {
  id: string;
  title: string;
  subtitle?: string;
  icon: LucideIcon;
  variant?: IAFlowNodeVariant;
  tone?: string;
  position: {
    x: number;
    y: number;
  };
  children?: IAFlowTreeNode[];
  linksTo?: string[];
};

export type IAFlowNodeData = {
  id: string;
  title: string;
  subtitle?: string;
  icon: LucideIcon;
  variant: IAFlowNodeVariant;
  tone: string;
  isActive?: boolean;
};

export type IAFlowLegendMode = "areas" | "agents";

export type IAFlowLegendNodeData = {
  id: string;
  mode: IAFlowLegendMode;
  title: string;
  items: string[];
  activeItem?: string;
};

export type IAFlowCanvasNodeData = IAFlowNodeData | IAFlowLegendNodeData;
export type IAFlowCanvasNode = Node<IAFlowCanvasNodeData>;

export type IAFlowBuildOptions = {
  positionOverrides?: Record<string, { x: number; y: number }>;
  activeNodeIds?: Set<string>;
};
