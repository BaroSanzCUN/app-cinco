"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addEdge,
  Background,
  ConnectionMode,
  Controls,
  MarkerType,
  ReactFlow,
  reconnectEdge,
  type ReactFlowInstance,
  type Connection,
  type Edge,
  type Viewport,
  useEdgesState,
  useNodesState,
  type EdgeTypes,
  type NodeTypes,
} from "@xyflow/react";
import IAFlowEdge from "./edges/IAFlowEdge";
import IAFlowLegendNode from "./nodes/IAFlowLegendNode";
import IAFlowNode from "./nodes/IAFlowNode";
import { IA_DEV_FLOW_TREE } from "./flow.config";
import { buildFlowGraph } from "./buildFlowGraph";
import {
  loadFlowLayout,
  saveFlowLayout,
  type IADevPersistedEdge,
} from "../persistence/layoutStorage";
import type {
  IAFlowCanvasNode,
} from "./types";

const nodeTypes: NodeTypes = {
  iaFlowNode: IAFlowNode,
  iaFlowLegend: IAFlowLegendNode,
};

const edgeTypes: EdgeTypes = {
  iaFlowEdge: IAFlowEdge,
};

const HISTORY_LIMIT = 30;
const AREAS_NODE_ID = "legend-areas";
const AGENTS_NODE_ID = "legend-agents";
const EDGE_LABELS_BY_ID: Record<string, string> = {
  "check->alert": "NO",
  "check->audit": "SI",
  "audit->result": "SI",
  "audit->alert": "NO",
  "route->meta": "SI",
  "route->result": "NO",
};
const getEdgeLabel = (edgeId: string, source: string, target: string) =>
  EDGE_LABELS_BY_ID[edgeId] ?? EDGE_LABELS_BY_ID[`${source}->${target}`];

type FlowSnapshot = {
  nodes: IAFlowCanvasNode[];
  edges: Edge[];
  viewport: Viewport;
  signature: string;
};

const cloneNodes = (nodes: IAFlowCanvasNode[]) =>
  nodes.map((node) => ({
    ...node,
    position: { ...node.position },
    data: { ...node.data },
  }));

const cloneEdges = (edges: Edge[]) =>
  edges.map((edge) => ({
    ...edge,
    markerEnd: edge.markerEnd,
    style: edge.style ? { ...edge.style } : undefined,
  }));

const buildSignature = (
  nodes: IAFlowCanvasNode[],
  edges: Edge[],
  viewport: Viewport,
) =>
  JSON.stringify({
    nodes: nodes
      .map((node) => ({
        id: node.id,
        x: Math.round(node.position.x * 100) / 100,
        y: Math.round(node.position.y * 100) / 100,
      }))
      .sort((a, b) => a.id.localeCompare(b.id)),
    edges: edges
      .map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle ?? null,
        targetHandle: edge.targetHandle ?? null,
      }))
      .sort((a, b) => a.id.localeCompare(b.id)),
    viewport: {
      x: Math.round(viewport.x * 100) / 100,
      y: Math.round(viewport.y * 100) / 100,
      zoom: Math.round(viewport.zoom * 1000) / 1000,
    },
  });

const buildEdgeStyle = (edgeId?: string, source?: string, target?: string) => ({
  type: "iaFlowEdge" as const,
  animated: false,
  reconnectable: true,
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 18,
    height: 18,
    color: "#e2e8f0",
  },
  style: {
    stroke: "#e2e8f0",
    strokeWidth: 2,
  },
  data:
    edgeId && source && target && getEdgeLabel(edgeId, source, target)
      ? { label: getEdgeLabel(edgeId, source, target) }
      : undefined,
});

const toPersistedEdges = (edges: Edge[]): IADevPersistedEdge[] =>
  edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle ?? null,
    targetHandle: edge.targetHandle ?? null,
  }));

const toRuntimeEdges = (edges: IADevPersistedEdge[]): Edge[] =>
  edges.map((edge) => ({
    ...edge,
    ...buildEdgeStyle(edge.id, edge.source, edge.target),
  }));

type IADevFlowCanvasProps = {
  activeNodeIds?: string[];
  serviceAreas?: string[];
  availableAgents?: string[];
  activeArea?: string;
  activeAgent?: string;
};

const IADevFlowCanvas = ({
  activeNodeIds = [],
  serviceAreas = [],
  availableAgents = [],
  activeArea,
  activeAgent,
}: IADevFlowCanvasProps) => {
  const activeNodeSet = useMemo(() => new Set(activeNodeIds), [activeNodeIds]);
  const persistedLayout = useMemo(() => loadFlowLayout(), []);
  const { nodes: baseNodes, edges: baseEdges } = useMemo(
    () =>
      buildFlowGraph(IA_DEV_FLOW_TREE, {
        positionOverrides: persistedLayout?.nodePositions,
      }),
    [persistedLayout],
  );
  const legendNodes = useMemo<IAFlowCanvasNode[]>(
    () => [
      {
        id: AREAS_NODE_ID,
        type: "iaFlowLegend",
        position: persistedLayout?.nodePositions?.[AREAS_NODE_ID] ?? { x: 14, y: 20 },
        draggable: true,
        selectable: true,
        connectable: false,
        deletable: false,
        focusable: true,
        data: {
          id: AREAS_NODE_ID,
          mode: "areas",
          title: "Areas",
          items: serviceAreas,
          activeItem: activeArea,
        },
      },
      {
        id: AGENTS_NODE_ID,
        type: "iaFlowLegend",
        position: persistedLayout?.nodePositions?.[AGENTS_NODE_ID] ?? { x: 190, y: 20 },
        draggable: true,
        selectable: true,
        connectable: false,
        deletable: false,
        focusable: true,
        data: {
          id: AGENTS_NODE_ID,
          mode: "agents",
          title: "Agentes",
          items: availableAgents,
          activeItem: activeAgent,
        },
      },
    ],
    [activeAgent, activeArea, availableAgents, persistedLayout?.nodePositions, serviceAreas],
  );
  const initialNodes = useMemo(
    () => cloneNodes([...baseNodes, ...legendNodes]),
    [baseNodes, legendNodes],
  );
  const initialEdges = useMemo(() => {
    const nodeIds = new Set(initialNodes.map((node) => node.id));
    if (persistedLayout) {
      const isLayoutBeforeRouteNode =
        !Object.prototype.hasOwnProperty.call(
          persistedLayout.nodePositions ?? {},
          "route",
        );
      if (isLayoutBeforeRouteNode) {
        return cloneEdges(baseEdges);
      }
      const validPersistedEdges = (persistedLayout.edges ?? []).filter(
        (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target),
      );
      return toRuntimeEdges(validPersistedEdges);
    }
    return cloneEdges(baseEdges);
  }, [baseEdges, initialNodes, persistedLayout]);

  const initialViewport = useMemo<Viewport>(
    () =>
      persistedLayout?.viewport ?? {
        x: 0,
        y: 0,
        zoom: 1,
      },
    [persistedLayout?.viewport],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [viewportState, setViewportState] = useState<Viewport>(initialViewport);
  const flowRef = useRef<ReactFlowInstance<IAFlowCanvasNode, Edge> | null>(
    null,
  );
  const isRestoringRef = useRef(false);
  const historyRef = useRef<FlowSnapshot[]>([]);
  const historyIndexRef = useRef(-1);

  const applySnapshot = useCallback(
    (snapshot: FlowSnapshot) => {
      isRestoringRef.current = true;
      setNodes(cloneNodes(snapshot.nodes));
      setEdges(cloneEdges(snapshot.edges));
      setViewportState({ ...snapshot.viewport });
      flowRef.current?.setViewport(snapshot.viewport, { duration: 0 });
      window.setTimeout(() => {
        isRestoringRef.current = false;
      }, 0);
    },
    [setEdges, setNodes],
  );

  const commitSnapshot = useCallback(
    (
      snapshotNodes: IAFlowCanvasNode[],
      snapshotEdges: Edge[],
      snapshotViewport: Viewport,
      mode: "push" | "reset" = "push",
    ) => {
      const signature = buildSignature(
        snapshotNodes,
        snapshotEdges,
        snapshotViewport,
      );
      const snapshot: FlowSnapshot = {
        nodes: cloneNodes(snapshotNodes),
        edges: cloneEdges(snapshotEdges),
        viewport: { ...snapshotViewport },
        signature,
      };

      if (mode === "reset") {
        historyRef.current = [snapshot];
        historyIndexRef.current = 0;
        return;
      }

      const current = historyRef.current[historyIndexRef.current];
      if (current?.signature === signature) return;

      const trimmed = historyRef.current.slice(0, historyIndexRef.current + 1);
      trimmed.push(snapshot);

      const overflow = Math.max(0, trimmed.length - HISTORY_LIMIT);
      const nextHistory = overflow > 0 ? trimmed.slice(overflow) : trimmed;

      historyRef.current = nextHistory;
      historyIndexRef.current = nextHistory.length - 1;
    },
    [],
  );

  const undo = useCallback(() => {
    if (historyIndexRef.current <= 0) return;
    historyIndexRef.current -= 1;
    const snapshot = historyRef.current[historyIndexRef.current];
    if (!snapshot) return;
    applySnapshot(snapshot);
  }, [applySnapshot]);

  const redo = useCallback(() => {
    if (historyIndexRef.current >= historyRef.current.length - 1) return;
    historyIndexRef.current += 1;
    const snapshot = historyRef.current[historyIndexRef.current];
    if (!snapshot) return;
    applySnapshot(snapshot);
  }, [applySnapshot]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((prevEdges) =>
        addEdge(
          {
            ...connection,
            ...buildEdgeStyle(undefined, connection.source, connection.target),
          },
          prevEdges,
        ),
      );
    },
    [setEdges],
  );

  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      setEdges((prevEdges) => reconnectEdge(oldEdge, newConnection, prevEdges));
    },
    [setEdges],
  );

  const removeEdgeById = useCallback(
    (edgeId: string) => {
      setEdges((prevEdges) => prevEdges.filter((edge) => edge.id !== edgeId));
    },
    [setEdges],
  );

  useEffect(() => {
    commitSnapshot(initialNodes, initialEdges, initialViewport, "reset");
  }, [commitSnapshot, initialEdges, initialNodes, initialViewport]);

  useEffect(() => {
    setNodes((prevNodes) =>
      prevNodes.map((node) => ({
        ...node,
        data:
          node.type === "iaFlowNode"
            ? {
                ...node.data,
                isActive: activeNodeSet.has(node.id),
              }
            : node.id === AREAS_NODE_ID
              ? {
                  ...node.data,
                  items: serviceAreas,
                  activeItem: activeArea,
                }
              : node.id === AGENTS_NODE_ID
                ? {
                    ...node.data,
                    items: availableAgents,
                    activeItem: activeAgent,
                  }
                : node.data,
      })),
    );
  }, [activeAgent, activeArea, activeNodeSet, availableAgents, serviceAreas, setNodes]);

  useEffect(() => {
    if (isRestoringRef.current) return;

    const timer = window.setTimeout(() => {
      commitSnapshot(nodes, edges, viewportState, "push");
    }, 180);

    return () => window.clearTimeout(timer);
  }, [commitSnapshot, edges, nodes, viewportState]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isModifier = event.ctrlKey || event.metaKey;
      if (!isModifier) return;

      const key = event.key.toLowerCase();
      if (key === "z" && !event.shiftKey) {
        event.preventDefault();
        undo();
        return;
      }

      if (key === "y" || (key === "z" && event.shiftKey)) {
        event.preventDefault();
        redo();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [redo, undo]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const nodePositions = Object.fromEntries(
        nodes.map((node) => [node.id, node.position]),
      );
      saveFlowLayout({
        nodePositions,
        edges: toPersistedEdges(edges),
        viewport: viewportState,
      });
    }, 80);

    return () => window.clearTimeout(timer);
  }, [edges, nodes, viewportState]);

  return (
    <div
      className="relative h-full min-h-[420px] overflow-hidden rounded-xl border border-gray-700/30 bg-slate-900"
      style={{
        backgroundImage:
          "linear-gradient(rgba(148,163,184,.15) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,.15) 1px, transparent 1px)",
        backgroundSize: "24px 24px",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onInit={(instance) => {
          flowRef.current = instance;
        }}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onReconnect={onReconnect}
        onEdgeDoubleClick={(_, edge) => removeEdgeById(edge.id)}
        onEdgeContextMenu={(event, edge) => {
          event.preventDefault();
          removeEdgeById(edge.id);
        }}
        nodesConnectable
        edgesReconnectable
        elementsSelectable
        deleteKeyCode={["Backspace", "Delete"]}
        connectOnClick={false}
        connectionMode={ConnectionMode.Loose}
        defaultViewport={initialViewport}
        onMoveEnd={(_, viewport) => setViewportState(viewport)}
        onEdgesDelete={(deletedEdges) => {
          const deletedIds = new Set(deletedEdges.map((edge) => edge.id));
          setEdges((prev) => prev.filter((edge) => !deletedIds.has(edge.id)));
        }}
        onNodesDelete={(deletedNodes) => {
          const deletedIds = new Set(deletedNodes.map((node) => node.id));
          setNodes((prev) => prev.filter((node) => !deletedIds.has(node.id)));
          setEdges((prev) =>
            prev.filter(
              (edge) =>
                !deletedIds.has(edge.source) && !deletedIds.has(edge.target),
            ),
          );
        }}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.5, maxZoom: 1.6 }}
        minZoom={0.35}
        maxZoom={1.8}
        defaultEdgeOptions={{ type: "iaFlowEdge" }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(148,163,184,.16)" gap={24} size={1} />
        <Controls
          position="bottom-right"
          className="[&>button]:!border-gray-700 [&>button]:!bg-gray-900/85 [&>button]:!text-white [&>button:hover]:!bg-gray-800"
        />
      </ReactFlow>
    </div>
  );
};

export default IADevFlowCanvas;
