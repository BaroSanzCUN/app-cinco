"use client";

export type IADevNodePositionMap = Record<string, { x: number; y: number }>;

export type IADevPersistedEdge = {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
};

export type IADevFlowLayoutState = {
  version: 1;
  nodePositions: IADevNodePositionMap;
  edges: IADevPersistedEdge[];
  viewport: {
    x: number;
    y: number;
    zoom: number;
  };
  updatedAt: string;
};

export type IADevWorkspaceState = {
  version: 1;
  leftOpen: boolean;
  rightOpen: boolean;
  leftWidth: number;
  rightWidth: number;
  updatedAt: string;
};

const FLOW_KEY = "ia-dev.flow-layout.v1";
const WORKSPACE_KEY = "ia-dev.workspace.v1";

const safeParse = <T>(raw: string | null): T | null => {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

export const loadFlowLayout = (): IADevFlowLayoutState | null => {
  if (typeof window === "undefined") return null;
  const parsed = safeParse<IADevFlowLayoutState>(localStorage.getItem(FLOW_KEY));
  if (!parsed || parsed.version !== 1) return null;
  return parsed;
};

export const saveFlowLayout = (
  state: Omit<IADevFlowLayoutState, "version" | "updatedAt">,
) => {
  if (typeof window === "undefined") return;
  const payload: IADevFlowLayoutState = {
    version: 1,
    nodePositions: state.nodePositions,
    edges: state.edges,
    viewport: state.viewport,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(FLOW_KEY, JSON.stringify(payload));
};

export const loadWorkspaceLayout = (): IADevWorkspaceState | null => {
  if (typeof window === "undefined") return null;
  const parsed = safeParse<IADevWorkspaceState>(
    localStorage.getItem(WORKSPACE_KEY),
  );
  if (!parsed || parsed.version !== 1) return null;
  return parsed;
};

export const saveWorkspaceLayout = (
  state: Omit<IADevWorkspaceState, "version" | "updatedAt">,
) => {
  if (typeof window === "undefined") return;
  const payload: IADevWorkspaceState = {
    version: 1,
    leftOpen: state.leftOpen,
    rightOpen: state.rightOpen,
    leftWidth: state.leftWidth,
    rightWidth: state.rightWidth,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(WORKSPACE_KEY, JSON.stringify(payload));
};
