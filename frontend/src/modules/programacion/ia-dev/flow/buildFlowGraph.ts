import { MarkerType, type Edge, type Node } from "@xyflow/react";
import type {
  IAFlowBuildOptions,
  IAFlowNodeData,
  IAFlowTreeNode,
} from "./types";

const DEFAULT_TONE = "bg-gray-700/90";

const makeEdgeId = (source: string, target: string) => `${source}->${target}`;
const EDGE_LABELS_BY_ID: Record<string, string> = {
  "check->alert": "NO",
  "check->audit": "SI",
  "audit->result": "SI",
  "audit->alert": "NO",
  "route->meta": "SI",
  "route->result": "NO",
};
const getEdgeLabel = (id: string, source: string, target: string) =>
  EDGE_LABELS_BY_ID[id] ?? EDGE_LABELS_BY_ID[`${source}->${target}`];

export const buildFlowGraph = (
  root: IAFlowTreeNode,
  options?: IAFlowBuildOptions,
): {
  nodes: Node<IAFlowNodeData>[];
  edges: Edge[];
} => {
  const nodeMap = new Map<string, Node<IAFlowNodeData>>();
  const edgeMap = new Map<string, Edge>();

  const ensureNode = (node: IAFlowTreeNode) => {
    if (nodeMap.has(node.id)) return;

    nodeMap.set(node.id, {
      id: node.id,
      position: options?.positionOverrides?.[node.id] ?? node.position,
      type: "iaFlowNode",
      draggable: true,
      data: {
        id: node.id,
        title: node.title,
        subtitle: node.subtitle,
        icon: node.icon,
        variant: node.variant ?? "split",
        tone: node.tone ?? DEFAULT_TONE,
        isActive: options?.activeNodeIds?.has(node.id) ?? false,
      },
    });
  };

  const ensureEdge = (source: string, target: string) => {
    const id = makeEdgeId(source, target);
    if (edgeMap.has(id)) return;

    edgeMap.set(id, {
      id,
      source,
      target,
      sourceHandle: "source-right",
      targetHandle: "target-left",
      type: "iaFlowEdge",
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
      data: getEdgeLabel(id, source, target)
        ? { label: getEdgeLabel(id, source, target) }
        : undefined,
    });
  };

  const walk = (node: IAFlowTreeNode, parentId?: string) => {
    ensureNode(node);

    if (parentId) {
      ensureEdge(parentId, node.id);
    }

    node.children?.forEach((child) => walk(child, node.id));
    node.linksTo?.forEach((targetId) => ensureEdge(node.id, targetId));
  };

  walk(root);

  return {
    nodes: [...nodeMap.values()],
    edges: [...edgeMap.values()],
  };
};
