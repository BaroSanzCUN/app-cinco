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

const DEFAULT_FLOW_LAYOUT: IADevFlowLayoutState = {
  version: 1,
  nodePositions: {
    q: { x: -73.24900917965589, y: 314.32710787983393 },
    gpt: { x: 156.6009382286789, y: 314.033049846081 },
    route: { x: 373.7137806051453, y: 314.60214995954914 },
    meta: { x: 254.47534621112698, y: 169.75867599178136 },
    aus: { x: 470, y: 70 },
    join: { x: 647.2828981971873, y: 292.440063862291 },
    rules: { x: 906.470431070465, y: 293.30847107354253 },
    check: { x: 659.3803676249859, y: 413.7468228612044 },
    alert: { x: 430, y: 560 },
    audit: { x: 985.792163345598, y: 414.8266770021946 },
    result: { x: 146.6403679258427, y: 606.3887144575934 },
    personal: { x: 630, y: 70 },
    transport: { x: 790, y: 70 },
    operacion: { x: 950, y: 70 },
    "legend-areas": { x: 14, y: 20 },
    "legend-agents": { x: 178.85266890427113, y: -53.2492566419555 },
  },
  edges: [
    {
      id: "gpt->route",
      source: "gpt",
      target: "route",
      sourceHandle: "source-right",
      targetHandle: "target-left",
    },
    {
      id: "join->rules",
      source: "join",
      target: "rules",
      sourceHandle: "source-right",
      targetHandle: "target-left",
    },
    {
      id: "rules->check",
      source: "rules",
      target: "check",
      sourceHandle: "source-right",
      targetHandle: "target-left",
    },
    {
      id: "xy-edge__qsource-right-gpttarget-left",
      source: "q",
      target: "gpt",
      sourceHandle: "source-right",
      targetHandle: "target-left",
    },
    {
      id: "xy-edge__metasource-top-aussource-top",
      source: "meta",
      target: "aus",
      sourceHandle: "source-top",
      targetHandle: "source-top",
    },
    {
      id: "xy-edge__metasource-top-personaltarget-top",
      source: "meta",
      target: "personal",
      sourceHandle: "source-top",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__metasource-top-transporttarget-top",
      source: "meta",
      target: "transport",
      sourceHandle: "source-top",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__metasource-top-operaciontarget-top",
      source: "meta",
      target: "operacion",
      sourceHandle: "source-top",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__aussource-bottom-jointarget-top",
      source: "aus",
      target: "join",
      sourceHandle: "source-bottom",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__personalsource-bottom-jointarget-top",
      source: "personal",
      target: "join",
      sourceHandle: "source-bottom",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__transportsource-bottom-jointarget-top",
      source: "transport",
      target: "join",
      sourceHandle: "source-bottom",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__operacionsource-bottom-jointarget-top",
      source: "operacion",
      target: "join",
      sourceHandle: "source-bottom",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__routesource-bottom-resulttarget-top",
      source: "route",
      target: "result",
      sourceHandle: "source-bottom",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__auditsource-right-resulttarget-bottom",
      source: "audit",
      target: "result",
      sourceHandle: "source-right",
      targetHandle: "target-bottom",
    },
    {
      id: "xy-edge__auditsource-bottom-alerttarget-right",
      source: "audit",
      target: "alert",
      sourceHandle: "source-bottom",
      targetHandle: "target-right",
    },
    {
      id: "xy-edge__checksource-right-audittarget-left",
      source: "check",
      target: "audit",
      sourceHandle: "source-right",
      targetHandle: "target-left",
    },
    {
      id: "xy-edge__checksource-bottom-alerttarget-top",
      source: "check",
      target: "alert",
      sourceHandle: "source-bottom",
      targetHandle: "target-top",
    },
    {
      id: "xy-edge__routesource-top-metatarget-bottom",
      source: "route",
      target: "meta",
      sourceHandle: "source-top",
      targetHandle: "target-bottom",
    },
  ],
  viewport: {
    x: 259.42203020128204,
    y: 52.49694814865498,
    zoom: 0.6093853943072872,
  },
  updatedAt: "2026-03-30T19:21:44.751Z",
};

const safeParse = <T>(raw: string | null): T | null => {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

const cloneFlowLayout = (state: IADevFlowLayoutState): IADevFlowLayoutState => ({
  version: 1,
  nodePositions: Object.fromEntries(
    Object.entries(state.nodePositions).map(([id, position]) => [
      id,
      { x: position.x, y: position.y },
    ]),
  ),
  edges: state.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle ?? null,
    targetHandle: edge.targetHandle ?? null,
  })),
  viewport: {
    x: state.viewport.x,
    y: state.viewport.y,
    zoom: state.viewport.zoom,
  },
  updatedAt: state.updatedAt,
});

export const loadFlowLayout = (): IADevFlowLayoutState | null => {
  if (typeof window === "undefined") return cloneFlowLayout(DEFAULT_FLOW_LAYOUT);
  const parsed = safeParse<IADevFlowLayoutState>(localStorage.getItem(FLOW_KEY));
  if (parsed && parsed.version === 1) return cloneFlowLayout(parsed);
  localStorage.setItem(FLOW_KEY, JSON.stringify(DEFAULT_FLOW_LAYOUT));
  return cloneFlowLayout(DEFAULT_FLOW_LAYOUT);
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
