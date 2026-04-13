"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import {
  Bot,
  ChevronsLeft,
  ChevronsRight,
  Database,
  FastForward,
  GripHorizontal,
  Loader2,
  Maximize2,
  MessageSquare,
  Minimize2,
  Minus,
  Pause,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Plus,
  Rewind,
  RotateCcw,
  SendHorizonal,
  SkipBack,
  SkipForward,
} from "lucide-react";
import IADevFlowCanvas from "./flow/IADevFlowCanvas";
import IADevChartPanel from "./components/IADevChartPanel";
import IADevMemoryPanel from "./components/IADevMemoryPanel";
import {
  loadWorkspaceLayout,
  saveWorkspaceLayout,
} from "./persistence/layoutStorage";
import {
  createIADevTicket,
  getIADevHealth,
  resetIADevMemory,
  type IADevAction,
  type IADevChartPayload,
  type IADevChatResponse,
  type IADevMemoryCandidate,
  type IADevMemoryProposal,
  sendIADevMessage,
} from "@/services/ia-dev.service";

type ResizeSide = "left" | "right" | null;

const LEFT_RAIL_WIDTH = 56;
const LEFT_COLLAPSE_THRESHOLD = 72;
const RIGHT_COLLAPSE_THRESHOLD = 150;
const DEFAULT_LEFT_WIDTH = 300;
const DEFAULT_RIGHT_WIDTH = 360;
const PANEL_STEP = 32;
const TERMINAL_MIN_HEIGHT = 105;
const TERMINAL_DEFAULT_HEIGHT = 220;

const DATABASES = [
  {
    name: "cincosas_cincosas",
    tables: [
      "gestionh_ausentismo",
      "dictionary_tables",
      "dictionary_columns",
      "dictionary_relations",
    ],
  },
  {
    name: "cinco_base_de_personal",
    tables: ["cinco_base_de_personal", "supervisores", "cargos", "areas"],
  },
];

const SERVICE_AREAS = [
  { id: "HHGG", domains: ["attendance", "rrhh"] },
  { id: "OPERACIONES", domains: ["operations"] },
  { id: "TRANSPORTE", domains: ["transport"] },
  { id: "VIATICOS", domains: ["viatics"] },
  { id: "NOMINA", domains: ["payroll"] },
  { id: "AUDITORIA", domains: ["audit"] },
];

const AVAILABLE_AGENTS = [
  "analista_agent",
  "rrhh_agent",
  "attendance_agent",
  "transport_agent",
  "operations_agent",
  "viatics_agent",
  "payroll_agent",
  "audit_agent",
];

const BASE_ACTIVE_NODE_IDS: string[] = [];

const getAreaFromDomain = (domain?: string | null) => {
  const domainKey = (domain || "").toLowerCase();
  const match = SERVICE_AREAS.find((area) => area.domains.includes(domainKey));
  return match?.id || "HHGG";
};

const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));

const asChartPayload = (value: unknown): IADevChartPayload | null => {
  if (!value || typeof value !== "object") return null;
  const candidate = value as IADevChartPayload;
  if (
    candidate.type ||
    (Array.isArray(candidate.points) && candidate.points.length > 0) ||
    (Array.isArray(candidate.labels) && candidate.labels.length > 0) ||
    (Array.isArray(candidate.data) && candidate.data.length > 0)
  ) {
    return candidate;
  }
  return null;
};

const extractChartFromResponse = (result: IADevChatResponse): IADevChartPayload | null => {
  const chartDirect = asChartPayload(result.data?.chart);
  if (chartDirect) return chartDirect;

  const chartFromArray = Array.isArray(result.data?.charts)
    ? asChartPayload(result.data?.charts[0])
    : null;
  if (chartFromArray) return chartFromArray;

  const chartAction = (result.actions || []).find((action) => action.type === "render_chart");
  if (!chartAction) return null;
  return asChartPayload(chartAction.payload?.chart);
};

const ResizeHandle = ({ onMouseDown }: { onMouseDown: () => void }) => (
  <button
    aria-label="Resize panel"
    onMouseDown={onMouseDown}
    className="group relative w-2 shrink-0 cursor-col-resize bg-gray-50 transition hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-800"
  >
    <span className="absolute top-1/2 left-1/2 h-14 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gray-300 group-hover:bg-brand-500 dark:bg-gray-700 dark:group-hover:bg-brand-400" />
  </button>
);

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  actions?: IADevAction[];
  memoryCandidates?: IADevMemoryCandidate[];
  pendingProposals?: IADevMemoryProposal[];
};

type ProcessRun = {
  id: string;
  createdAt: number;
  query: string;
  reply: string;
  agent: string;
  domain: string;
  usedTools: string[];
  channels: string[];
  trace: IADevChatResponse["trace"];
  activeNodes: string[];
};

const IADevWorkspace = () => {
  const workspaceRef = useRef<HTMLDivElement>(null);
  const centerSectionRef = useRef<HTMLElement>(null);
  const initialWorkspaceLayout = useMemo(() => loadWorkspaceLayout(), []);
  const [leftOpen, setLeftOpen] = useState(
    initialWorkspaceLayout?.leftOpen ?? true,
  );
  const [rightOpen, setRightOpen] = useState(
    initialWorkspaceLayout?.rightOpen ?? true,
  );
  const [leftWidth, setLeftWidth] = useState(
    initialWorkspaceLayout?.leftWidth ?? DEFAULT_LEFT_WIDTH,
  );
  const [rightWidth, setRightWidth] = useState(
    initialWorkspaceLayout?.rightWidth ?? DEFAULT_RIGHT_WIDTH,
  );
  const [resizeSide, setResizeSide] = useState<ResizeSide>(null);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "IA DEV listo. Describe una consulta y te muestro agente, tools y trazabilidad.",
    },
  ]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatStatus, setChatStatus] = useState("");
  const [latestMemoryCandidates, setLatestMemoryCandidates] = useState<
    IADevMemoryCandidate[]
  >([]);
  const [latestPendingProposals, setLatestPendingProposals] = useState<
    IADevMemoryProposal[]
  >([]);
  const [latestMemoryActions, setLatestMemoryActions] = useState<IADevAction[]>(
    [],
  );
  const [activeChart, setActiveChart] = useState<IADevChartPayload | null>(null);
  const [activeAgent, setActiveAgent] = useState<string>("analista_agent");
  const [activeArea, setActiveArea] = useState<string>("HHGG");
  const [activeNodeIds, setActiveNodeIds] = useState<string[]>(BASE_ACTIVE_NODE_IDS);
  const [aiDictionaryStatus, setAiDictionaryStatus] = useState<{
    ok: boolean;
    table?: string | null;
    rows?: number;
    error?: string;
  } | null>(null);
  const [runHistory, setRunHistory] = useState<ProcessRun[]>([]);
  const [selectedRunIndex, setSelectedRunIndex] = useState(-1);
  const [selectedStepIndex, setSelectedStepIndex] = useState(0);
  const [isPlaybackRunning, setIsPlaybackRunning] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<0.5 | 1 | 2>(1);
  const [terminalHeight, setTerminalHeight] = useState(TERMINAL_DEFAULT_HEIGHT);
  const [terminalDetached, setTerminalDetached] = useState(false);
  const [resizingTerminal, setResizingTerminal] = useState(false);

  const selectedRun = selectedRunIndex >= 0 ? runHistory[selectedRunIndex] : null;
  const selectedTrace = selectedRun?.trace ?? [];
  const maxStepIndex = Math.max(0, selectedTrace.length - 1);
  const currentStep = selectedTrace[selectedStepIndex] ?? null;
  const resolveStepActiveNodes = (run: ProcessRun | null, stepIndex: number) => {
    if (!run) return BASE_ACTIVE_NODE_IDS;
    const step = run.trace[stepIndex];
    if (step?.active_nodes && step.active_nodes.length > 0) {
      return step.active_nodes;
    }
    if (run.activeNodes.length > 0) {
      return run.activeNodes;
    }
    return BASE_ACTIVE_NODE_IDS;
  };

  const stringifyDetail = (detail: unknown) => {
    if (detail == null) return "";
    if (typeof detail === "string") return detail;
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  };

  const getWorkspaceWidth = () =>
    workspaceRef.current?.getBoundingClientRect().width ?? 0;

  const getMaxLeftWidth = () => {
    const reserved = LEFT_RAIL_WIDTH + (rightOpen ? rightWidth : 0);
    return Math.max(0, getWorkspaceWidth() - reserved);
  };

  const getMaxRightWidth = () => {
    const reserved = LEFT_RAIL_WIDTH + (leftOpen ? leftWidth : 0);
    return Math.max(0, getWorkspaceWidth() - reserved);
  };

  const openLeftPanel = () => {
    setLeftOpen(true);
    setLeftWidth((prev) => {
      const next = prev > LEFT_COLLAPSE_THRESHOLD ? prev : DEFAULT_LEFT_WIDTH;
      return clamp(next, 0, getMaxLeftWidth());
    });
  };

  const openRightPanel = () => {
    setRightOpen(true);
    setRightWidth((prev) => {
      const next = prev >= RIGHT_COLLAPSE_THRESHOLD ? prev : DEFAULT_RIGHT_WIDTH;
      return clamp(next, 0, getMaxRightWidth());
    });
  };

  const reduceLeftPanel = () => {
    setLeftWidth((prev) => {
      const next = Math.max(0, prev - PANEL_STEP);
      if (next < LEFT_COLLAPSE_THRESHOLD) {
        setLeftOpen(false);
        return 0;
      }
      return next;
    });
  };

  const expandLeftPanel = () => {
    setLeftOpen(true);
    setLeftWidth((prev) => {
      const base = prev > LEFT_COLLAPSE_THRESHOLD ? prev : DEFAULT_LEFT_WIDTH;
      return clamp(base + PANEL_STEP, 0, getMaxLeftWidth());
    });
  };

  const reduceRightPanel = () => {
    setRightWidth((prev) => {
      const next = Math.max(0, prev - PANEL_STEP);
      if (next < RIGHT_COLLAPSE_THRESHOLD) {
        setRightOpen(false);
        return 0;
      }
      return next;
    });
  };

  const expandRightPanel = () => {
    setRightOpen(true);
    setRightWidth((prev) => {
      const base = prev >= RIGHT_COLLAPSE_THRESHOLD ? prev : DEFAULT_RIGHT_WIDTH;
      return clamp(base + PANEL_STEP, 0, getMaxRightWidth());
    });
  };

  useEffect(() => {
    if (!resizeSide) return;

    const onMouseMove = (event: MouseEvent) => {
      const container = workspaceRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();

      if (resizeSide === "left" && leftOpen) {
        const maxAllowed = Math.max(
          0,
          rect.width - LEFT_RAIL_WIDTH - (rightOpen ? rightWidth : 0),
        );
        const next = clamp(event.clientX - rect.left - LEFT_RAIL_WIDTH, 0, maxAllowed);
        if (next < LEFT_COLLAPSE_THRESHOLD) {
          setLeftOpen(false);
          setLeftWidth(0);
          return;
        }
        setLeftWidth(next);
      }

      if (resizeSide === "right" && rightOpen) {
        const maxAllowed = Math.max(
          0,
          rect.width - LEFT_RAIL_WIDTH - (leftOpen ? leftWidth : 0),
        );
        const next = clamp(rect.right - event.clientX, 0, maxAllowed);
        if (next < RIGHT_COLLAPSE_THRESHOLD) {
          setRightOpen(false);
          setRightWidth(0);
          return;
        }
        setRightWidth(next);
      }
    };

    const onMouseUp = () => {
      setResizeSide(null);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [leftOpen, leftWidth, resizeSide, rightOpen, rightWidth]);

  useEffect(() => {
    const syncPanelWidths = () => {
      const workspaceWidth = workspaceRef.current?.getBoundingClientRect().width ?? 0;

      if (leftOpen) {
        const maxLeft = Math.max(
          0,
          workspaceWidth - LEFT_RAIL_WIDTH - (rightOpen ? rightWidth : 0),
        );
        if (maxLeft < LEFT_COLLAPSE_THRESHOLD) {
          setLeftOpen(false);
          setLeftWidth(0);
        } else {
          setLeftWidth((prev) => clamp(prev, 0, maxLeft));
        }
      }

      if (rightOpen) {
        const maxRight = Math.max(
          0,
          workspaceWidth - LEFT_RAIL_WIDTH - (leftOpen ? leftWidth : 0),
        );
        if (maxRight < RIGHT_COLLAPSE_THRESHOLD) {
          setRightOpen(false);
          setRightWidth(0);
        } else {
          setRightWidth((prev) => clamp(prev, 0, maxRight));
        }
      }
    };

    syncPanelWidths();
    window.addEventListener("resize", syncPanelWidths);
    return () => window.removeEventListener("resize", syncPanelWidths);
  }, [leftOpen, rightOpen, leftWidth, rightWidth]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      saveWorkspaceLayout({
        leftOpen,
        rightOpen,
        leftWidth,
        rightWidth,
      });
    }, 180);

    return () => window.clearTimeout(timer);
  }, [leftOpen, rightOpen, leftWidth, rightWidth]);

  useEffect(() => {
    let active = true;

    const loadHealth = async () => {
      try {
        const health = await getIADevHealth();
        if (!active) return;
        setAiDictionaryStatus(health.data_sources.ai_dictionary);
      } catch {
        if (!active) return;
        setAiDictionaryStatus({
          ok: false,
          error: "No se pudo consultar ia-dev/health",
        });
      }
    };

    void loadHealth();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!isPlaybackRunning) return;
    if (selectedTrace.length === 0) return;
    if (selectedStepIndex >= selectedTrace.length - 1) {
      setIsPlaybackRunning(false);
      return;
    }

    const intervalMs = playbackSpeed === 0.5 ? 1800 : playbackSpeed === 2 ? 500 : 1000;
    const timer = window.setTimeout(() => {
      setSelectedStepIndex((prev) => Math.min(prev + 1, selectedTrace.length - 1));
    }, intervalMs);

    return () => window.clearTimeout(timer);
  }, [isPlaybackRunning, playbackSpeed, selectedStepIndex, selectedTrace.length]);

  useEffect(() => {
    if (!selectedRun) {
      setActiveNodeIds(BASE_ACTIVE_NODE_IDS);
      setActiveAgent("analista_agent");
      setActiveArea("HHGG");
      return;
    }

    setActiveNodeIds(resolveStepActiveNodes(selectedRun, selectedStepIndex));
    setActiveAgent(selectedRun.agent || "analista_agent");
    setActiveArea(getAreaFromDomain(selectedRun.domain));
  }, [selectedRun, selectedStepIndex]);

  useEffect(() => {
    if (!resizingTerminal || terminalDetached) return;

    const onMouseMove = (event: MouseEvent) => {
      const container = centerSectionRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const maxHeight = Math.max(
        TERMINAL_MIN_HEIGHT,
        Math.floor(rect.height * 0.75),
      );
      const nextHeight = clamp(
        rect.bottom - event.clientY - 16,
        TERMINAL_MIN_HEIGHT,
        maxHeight,
      );
      setTerminalHeight(nextHeight);
    };

    const onMouseUp = () => {
      setResizingTerminal(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [resizingTerminal, terminalDetached]);

  const submitChat = async () => {
    const value = chatInput.trim();
    if (!value || isSubmitting) return;

    setMessages((prev) => [...prev, { role: "user", content: value }]);
    setChatInput("");
    setIsPlaybackRunning(false);
    setSelectedStepIndex(0);
    setSelectedRunIndex(-1);
    setActiveNodeIds(BASE_ACTIVE_NODE_IDS);
    setActiveAgent("analista_agent");
    setActiveArea("HHGG");

    try {
      setIsSubmitting(true);
      const result = await sendIADevMessage({
        message: value,
        session_id: sessionId ?? undefined,
      });

      setSessionId(result.session_id);
      const usedTools =
        result.orchestrator.used_tools && result.orchestrator.used_tools.length > 0
          ? result.orchestrator.used_tools.join(", ")
          : "sin tools";

      const assistantMessage =
        `${result.reply}\n\n` +
        `Agente: ${result.orchestrator.selected_agent || "analista_agent"} | ` +
        `Dominio: ${result.orchestrator.domain || "general"} | ` +
        `Tools: ${usedTools}\n` +
        `Memoria: ${result.memory.used_messages}/${result.memory.capacity_messages} ` +
        `(${Math.round(result.memory.usage_ratio * 100)}%)`;

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: assistantMessage,
          actions: result.actions ?? [],
          memoryCandidates: result.memory_candidates ?? [],
          pendingProposals: result.pending_proposals ?? [],
        },
      ]);
      setLatestMemoryCandidates(result.memory_candidates ?? []);
      setLatestPendingProposals(result.pending_proposals ?? []);
      setLatestMemoryActions(result.actions ?? []);
      const chartFromResponse = extractChartFromResponse(result);
      if (chartFromResponse) {
        setActiveChart(chartFromResponse);
      }

      const channels = Array.from(
        new Set([
          `agent:${result.orchestrator.selected_agent || "analista_agent"}`,
          `domain:${result.orchestrator.domain || "general"}`,
          ...(result.orchestrator.used_tools ?? []).map((tool) => `tool:${tool}`),
          ...(result.trace ?? []).map((step) => `phase:${step.phase}`),
        ]),
      );
      const processRun: ProcessRun = {
        id: `${Date.now()}`,
        createdAt: Date.now(),
        query: value,
        reply: result.reply,
        agent: result.orchestrator.selected_agent || "analista_agent",
        domain: result.orchestrator.domain || "general",
        usedTools: result.orchestrator.used_tools ?? [],
        channels,
        trace: result.trace ?? [],
        activeNodes: result.active_nodes ?? [],
      };
      setRunHistory((prev) => {
        const next = [...prev, processRun].slice(-30);
        setSelectedRunIndex(next.length - 1);
        return next;
      });
      setSelectedStepIndex(0);
      setIsPlaybackRunning(false);

      setChatStatus(`Sesion ${result.session_id.slice(0, 8)} activa`);
      if (result.data_sources?.ai_dictionary) {
        setAiDictionaryStatus(result.data_sources.ai_dictionary);
      }
    } catch (error) {
      const detail =
        typeof error === "object" &&
        error &&
        "detail" in error &&
        typeof (error as { detail?: unknown }).detail === "string"
          ? (error as { detail: string }).detail
          : typeof error === "object" &&
              error &&
              "message" in error &&
              typeof (error as { message?: unknown }).message === "string"
            ? (error as { message: string }).message
            : "No fue posible procesar la consulta con IA DEV.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error de integracion IA DEV: ${detail}`,
        },
      ]);
      setChatStatus("Error de conexion con IA DEV");
    } finally {
      setIsSubmitting(false);
    }
  };

  const clearSessionMemory = async () => {
    if (!sessionId || isSubmitting) return;
    try {
      setIsSubmitting(true);
      await resetIADevMemory(sessionId);
      setActiveChart(null);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Memoria de la sesion reiniciada. Continuamos con contexto limpio.",
        },
      ]);
      setChatStatus(`Sesion ${sessionId.slice(0, 8)} reiniciada`);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "No fue posible reiniciar memoria en este momento.",
        },
      ]);
      setChatStatus("No se pudo reiniciar la memoria");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleActionClick = async (action: IADevAction) => {
    if (isSubmitting) return;
    if (action.type === "memory_review") {
      setChatStatus("Panel de memoria abierto para revisar propuestas y auditoria.");
      return;
    }
    if (action.type === "render_chart") {
      const chart = asChartPayload(action.payload?.chart);
      if (!chart) {
        setChatStatus("No se recibio un payload de grafica valido.");
        return;
      }
      setActiveChart(chart);
      setChatStatus("Grafica cargada desde la accion del agente.");
      return;
    }
    if (action.type !== "create_ticket") return;

    const title = action.payload?.title?.trim() || "Solicitud desde IA DEV";
    const description =
      action.payload?.description?.trim() ||
      "Solicitud generada desde interaccion IA DEV.";
    const category = action.payload?.category?.trim() || "general";

    try {
      setIsSubmitting(true);
      const created = await createIADevTicket({
        session_id: sessionId ?? undefined,
        title,
        description,
        category,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Ticket creado correctamente: ${created.ticket.ticket_id}. El equipo de desarrollo puede tomarlo desde ahora.`,
        },
      ]);
      setChatStatus(`Ticket ${created.ticket.ticket_id} creado`);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "No fue posible crear el ticket en este momento.",
        },
      ]);
      setChatStatus("Error al crear ticket");
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderTerminalPanel = (detached: boolean) => (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-gray-700/40 bg-slate-950 text-slate-200">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2 text-xs">
        <div className="min-w-0">
          <p className="truncate font-semibold text-slate-100">
            Consola Orquestador
          </p>
          {selectedRun ? (
            <p className="truncate text-[11px] text-slate-400">
              ultimo proceso: {selectedRun.query}
            </p>
          ) : (
            <p className="text-[11px] text-slate-500">
              aun no hay procesos registrados
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={openPreviousRun}
            className="rounded p-1 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedRunIndex <= 0}
            title="Proceso anterior"
          >
            <ChevronsLeft size={14} />
          </button>
          <button
            type="button"
            onClick={openNextRun}
            className="rounded p-1 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedRunIndex < 0 || selectedRunIndex >= runHistory.length - 1}
            title="Proceso siguiente"
          >
            <ChevronsRight size={14} />
          </button>
          <button
            type="button"
            onClick={() => setTerminalDetached((prev) => !prev)}
            className="rounded p-1 text-slate-300 hover:bg-slate-800"
            title={detached ? "Acoplar terminal" : "Desacoplar terminal"}
          >
            {detached ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      <div className="border-b border-slate-800 px-3 py-2">
        <div className="mb-2 flex flex-wrap gap-1">
          {selectedRun?.channels.slice(0, 12).map((channel) => (
            <span
              key={channel}
              className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] text-slate-300"
            >
              {channel}
            </span>
          ))}
        </div>
        <input
          type="range"
          min={0}
          max={maxStepIndex}
          value={selectedStepIndex}
          disabled={!selectedRun || selectedTrace.length === 0}
          onChange={(event) => {
            setIsPlaybackRunning(false);
            setSelectedStepIndex(Number(event.target.value));
          }}
          className="h-1.5 w-full cursor-pointer accent-brand-500"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-3 py-2 font-mono text-[11px] leading-5">
        {selectedRun && selectedTrace.length > 0 ? (
          <div className="space-y-1">
            {selectedTrace.slice(0, selectedStepIndex + 1).map((step, stepIndex) => (
              <div key={`${step.phase}-${stepIndex}`} className="text-slate-300">
                <span className="text-slate-500">[{step.at}]</span>{" "}
                <span className="text-cyan-300">{step.phase}</span>{" "}
                <span
                  className={
                    step.status === "ok"
                      ? "text-emerald-300"
                      : step.status === "warning"
                        ? "text-amber-300"
                        : "text-rose-300"
                  }
                >
                  ({step.status})
                </span>{" "}
                <span className="text-slate-200">{stringifyDetail(step.detail)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500">Esperando ejecucion del orquestador...</p>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-slate-800 px-3 py-2 text-xs">
        <div className="text-slate-400">
          paso {selectedTrace.length === 0 ? 0 : selectedStepIndex + 1}/{selectedTrace.length}
          {currentStep && (
            <span className="ml-2 text-slate-300">fase actual: {currentStep.phase}</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={goToFirstStep}
            className="rounded p-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedTrace.length === 0 || selectedStepIndex <= 0}
            title="Primer paso"
          >
            <SkipBack size={14} />
          </button>
          <button
            type="button"
            onClick={moveStepBackward}
            className="rounded p-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedTrace.length === 0 || selectedStepIndex <= 0}
            title="Paso anterior"
          >
            <Rewind size={14} />
          </button>
          <button
            type="button"
            onClick={() => setIsPlaybackRunning((prev) => !prev)}
            className="rounded p-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedTrace.length === 0}
            title={isPlaybackRunning ? "Pause" : "Play"}
          >
            {isPlaybackRunning ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            type="button"
            onClick={moveStepForward}
            className="rounded p-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedTrace.length === 0 || selectedStepIndex >= maxStepIndex}
            title="Paso siguiente"
          >
            <FastForward size={14} />
          </button>
          <button
            type="button"
            onClick={goToLastStep}
            className="rounded p-1 text-slate-200 hover:bg-slate-800 disabled:opacity-40"
            disabled={selectedTrace.length === 0 || selectedStepIndex >= maxStepIndex}
            title="Ultimo paso"
          >
            <SkipForward size={14} />
          </button>
          <button
            type="button"
            onClick={() => setPlaybackSpeed(0.5)}
            className={`rounded px-2 py-1 ${
              playbackSpeed === 0.5
                ? "bg-brand-500/25 text-brand-200"
                : "text-slate-300 hover:bg-slate-800"
            }`}
            title="Slow"
          >
            slow
          </button>
          <button
            type="button"
            onClick={() => setPlaybackSpeed(1)}
            className={`rounded px-2 py-1 ${
              playbackSpeed === 1
                ? "bg-brand-500/25 text-brand-200"
                : "text-slate-300 hover:bg-slate-800"
            }`}
            title="Normal"
          >
            1x
          </button>
          <button
            type="button"
            onClick={() => setPlaybackSpeed(2)}
            className={`rounded px-2 py-1 ${
              playbackSpeed === 2
                ? "bg-brand-500/25 text-brand-200"
                : "text-slate-300 hover:bg-slate-800"
            }`}
            title="Fast"
          >
            fast
          </button>
        </div>
      </div>
    </div>
  );

  const moveStepBackward = () => {
    setIsPlaybackRunning(false);
    setSelectedStepIndex((prev) => Math.max(0, prev - 1));
  };

  const moveStepForward = () => {
    setIsPlaybackRunning(false);
    setSelectedStepIndex((prev) => Math.min(maxStepIndex, prev + 1));
  };

  const goToFirstStep = () => {
    setIsPlaybackRunning(false);
    setSelectedStepIndex(0);
  };

  const goToLastStep = () => {
    setIsPlaybackRunning(false);
    setSelectedStepIndex(maxStepIndex);
  };

  const openPreviousRun = () => {
    if (runHistory.length === 0) return;
    setIsPlaybackRunning(false);
    setSelectedRunIndex((prev) => Math.max(0, prev - 1));
    setSelectedStepIndex(0);
  };

  const openNextRun = () => {
    if (runHistory.length === 0) return;
    setIsPlaybackRunning(false);
    setSelectedRunIndex((prev) => Math.min(runHistory.length - 1, prev + 1));
    setSelectedStepIndex(0);
  };

  return (
    <div className="w-full min-w-0 overflow-hidden">
      <PageBreadcrumb pageTitle={["Programacion", "IA DEV"]} />

      <div className="h-[calc(100vh-190px)] min-h-[650px] w-full min-w-0">
        <div
          ref={workspaceRef}
          className="flex h-full min-w-0 overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/3"
        >
          <aside className="flex w-14 shrink-0 flex-col items-center gap-2 border-r border-gray-200 bg-gray-50 py-3 dark:border-gray-800 dark:bg-gray-900">
            <button
              title="Bases de datos"
              onClick={() => {
                if (leftOpen) {
                  setLeftOpen(false);
                  return;
                }
                openLeftPanel();
              }}
              className={`inline-flex h-10 w-10 items-center justify-center rounded-lg transition ${
                leftOpen
                  ? "bg-brand-500 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              <Database size={18} />
            </button>
          </aside>

          {leftOpen && (
            <section
              className="flex shrink-0 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"
              style={{ width: leftWidth }}
            >
              <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2 dark:border-gray-800">
                <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
                  <Database size={16} />
                  <span className="truncate">Bases y tablas</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={reduceLeftPanel}
                    className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    title="Reducir"
                  >
                    <Minus size={14} />
                  </button>
                  <button
                    onClick={expandLeftPanel}
                    className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    title="Ampliar"
                  >
                    <Plus size={14} />
                  </button>
                  <button
                    onClick={() => setLeftOpen(false)}
                    className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    title="Contraer"
                  >
                    <PanelLeftClose size={16} />
                  </button>
                </div>
              </div>

              <div className="flex-1 space-y-4 overflow-auto p-3">
                <div className="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-800/70">
                  <p className="mb-2 text-sm font-semibold text-gray-800 dark:text-white/90">
                    ai_dictionary
                  </p>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                        aiDictionaryStatus?.ok
                          ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                          : "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
                      }`}
                    >
                      {aiDictionaryStatus?.ok ? "Conectado" : "Sin conexion"}
                    </span>
                    {typeof aiDictionaryStatus?.rows === "number" && (
                      <span className="text-xs text-gray-500 dark:text-gray-300">
                        filas: {aiDictionaryStatus.rows}
                      </span>
                    )}
                  </div>
                  {aiDictionaryStatus?.table && (
                    <p
                      className="mt-2 truncate text-xs text-gray-500 dark:text-gray-300"
                      title={aiDictionaryStatus.table}
                    >
                      {aiDictionaryStatus.table}
                    </p>
                  )}
                  {aiDictionaryStatus?.error && (
                    <p className="mt-2 text-xs text-red-600 dark:text-red-300">
                      {aiDictionaryStatus.error}
                    </p>
                  )}
                </div>

                {DATABASES.map((db) => (
                  <div
                    key={db.name}
                    className="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-800/70"
                  >
                    <p
                      className="mb-2 truncate text-sm font-semibold text-gray-800 dark:text-white/90"
                      title={db.name}
                    >
                      {db.name}
                    </p>
                    <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-300">
                      {db.tables.map((table) => (
                        <li
                          key={table}
                          title={table}
                          className="truncate rounded-md bg-white px-2 py-1 dark:bg-gray-900"
                        >
                          {table}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>
          )}

          {leftOpen && <ResizeHandle onMouseDown={() => setResizeSide("left")} />}

          <section ref={centerSectionRef} className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2 dark:border-gray-800">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
                <Bot size={16} />
                Flujo Multi-Agente (React Flow)
              </div>
              <div className="flex items-center gap-2">
                {!leftOpen && (
                  <button
                    onClick={openLeftPanel}
                    className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                  >
                    <PanelLeftOpen size={14} />
                    Abrir BD
                  </button>
                )}
                {!rightOpen && (
                  <button
                    onClick={openRightPanel}
                    className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                  >
                    <PanelRightOpen size={14} />
                    Abrir Chat
                  </button>
                )}
              </div>
            </div>

            <div className="relative min-h-0 flex flex-1 flex-col">
              <div className="relative min-h-0 flex-1 p-4">
                <IADevFlowCanvas
                  activeNodeIds={activeNodeIds}
                  serviceAreas={SERVICE_AREAS.map((area) => area.id)}
                  availableAgents={AVAILABLE_AGENTS}
                  activeArea={activeArea}
                  activeAgent={activeAgent}
                />

                {terminalDetached && (
                  <div className="pointer-events-none absolute inset-x-4 bottom-4 z-30 flex justify-end">
                    <div className="pointer-events-auto h-[320px] w-full max-w-[920px]">
                      {renderTerminalPanel(true)}
                    </div>
                  </div>
                )}
              </div>

              {!terminalDetached && (
                <>
                  <div className="mx-4 mb-1 flex items-center justify-center">
                    <button
                      type="button"
                      onMouseDown={() => setResizingTerminal(true)}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-700/60 bg-slate-900/80 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
                      title="Redimensionar terminal"
                    >
                      <GripHorizontal size={12} />
                      terminal
                    </button>
                  </div>
                  <div
                    className="mx-4 mb-4"
                    style={{ height: terminalHeight, minHeight: TERMINAL_MIN_HEIGHT }}
                  >
                    {renderTerminalPanel(false)}
                  </div>
                </>
              )}
            </div>
          </section>

          {rightOpen && <ResizeHandle onMouseDown={() => setResizeSide("right")} />}

          {rightOpen ? (
            <aside
              className="flex shrink-0 flex-col border-l border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"
              style={{ width: rightWidth }}
            >
              <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2 dark:border-gray-800">
                <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
                  <MessageSquare size={16} />
                  <span className="truncate">Chat IA</span>
                </div>
                <div className="flex items-center gap-1">
                  {sessionId && (
                    <button
                      onClick={clearSessionMemory}
                      className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                      title="Reiniciar memoria"
                      disabled={isSubmitting}
                    >
                      <RotateCcw size={14} />
                    </button>
                  )}
                  <button
                    onClick={reduceRightPanel}
                    className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    title="Reducir"
                  >
                    <Minus size={14} />
                  </button>
                  <button
                    onClick={expandRightPanel}
                    className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    title="Ampliar"
                  >
                    <Plus size={14} />
                  </button>
                  <button
                    onClick={() => setRightOpen(false)}
                    className="rounded-md p-1 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    title="Contraer"
                  >
                    <PanelRightClose size={16} />
                  </button>
                </div>
              </div>

              {chatStatus && (
                <div className="border-b border-gray-200 px-3 py-2 text-xs text-gray-500 dark:border-gray-800 dark:text-gray-300">
                  {chatStatus}
                </div>
              )}

              <IADevMemoryPanel
                latestCandidates={latestMemoryCandidates}
                latestPendingProposals={latestPendingProposals}
                latestActions={latestMemoryActions}
                isBusy={isSubmitting}
                onStatusChange={setChatStatus}
              />
              <IADevChartPanel
                chart={activeChart}
                onClose={() => setActiveChart(null)}
              />

              <div className="flex flex-1 flex-col gap-3 overflow-auto p-3">
                {messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`max-w-[92%] rounded-xl px-3 py-2 text-sm break-words whitespace-pre-wrap ${
                      message.role === "user"
                        ? "ml-auto bg-brand-500 text-white"
                        : "mr-auto border border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                    }`}
                  >
                    {message.content}
                    {message.role === "assistant" &&
                      message.pendingProposals &&
                      message.pendingProposals.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {message.pendingProposals.slice(0, 5).map((proposal) => (
                            <span
                              key={proposal.proposal_id}
                              className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                              title={`${proposal.proposal_id} · ${proposal.status}`}
                            >
                              {proposal.status}
                            </span>
                          ))}
                        </div>
                      )}
                    {message.role === "assistant" &&
                      message.memoryCandidates &&
                      message.memoryCandidates.length > 0 && (
                        <div className="mt-2 rounded-md border border-gray-200 bg-white/70 px-2 py-1 text-[11px] text-gray-600 dark:border-gray-700 dark:bg-gray-900/70 dark:text-gray-300">
                          Candidatos de memoria detectados:{" "}
                          {message.memoryCandidates.length}. Usa el panel
                          &quot;Memoria y Workflow&quot; para guardar preferencia, proponer
                          regla o ignorar.
                        </div>
                      )}
                    {message.role === "assistant" &&
                      message.actions &&
                      message.actions.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {message.actions.map((action) => (
                            <button
                              key={action.id}
                              type="button"
                              onClick={() => {
                                void handleActionClick(action);
                              }}
                              className="rounded-md border border-brand-300 bg-brand-500/10 px-2 py-1 text-xs font-semibold text-brand-700 transition hover:bg-brand-500/20 disabled:opacity-60 dark:border-brand-700 dark:text-brand-300"
                              disabled={isSubmitting}
                            >
                              {action.label}
                            </button>
                          ))}
                        </div>
                      )}
                  </div>
                ))}
              </div>

              <div className="border-t border-gray-200 p-3 dark:border-gray-800">
                <div className="flex items-end gap-2">
                  <textarea
                    rows={2}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        void submitChat();
                      }
                    }}
                    placeholder="Escribe tu consulta..."
                    className="min-h-[64px] flex-1 resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-brand-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                  />
                  <button
                    onClick={submitChat}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500 text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-70"
                    title="Enviar"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <SendHorizonal size={16} />
                    )}
                  </button>
                </div>
              </div>
            </aside>
          ) : (
            <aside className="flex w-12 shrink-0 items-start justify-center border-l border-gray-200 bg-gray-50 pt-3 dark:border-gray-800 dark:bg-gray-900">
              <button
                onClick={openRightPanel}
                title="Abrir chat"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
              >
                <PanelRightOpen size={16} />
              </button>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
};

export default IADevWorkspace;
