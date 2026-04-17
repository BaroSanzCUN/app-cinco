"use client";

import React, { useMemo, useRef, useState } from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { MessageSquare } from "lucide-react";
import ChatComposer from "@/modules/programacion/ia-dev/chat/components/ChatComposer";
import ChatMessageItem from "@/modules/programacion/ia-dev/chat/components/ChatMessage";
import ScrollToBottomButton from "@/modules/programacion/ia-dev/chat/components/ScrollToBottomButton";
import { type ChatMessageModel } from "@/modules/programacion/ia-dev/chat/types";
import { normalizeChatPayload } from "@/modules/programacion/ia-dev/chat/utils/normalizeChatPayload";
import { usePromptHistory } from "@/modules/programacion/ia-dev/chat/hooks/usePromptHistory";
import { useSmartAutoScroll } from "@/modules/programacion/ia-dev/chat/hooks/useSmartAutoScroll";
import { useIADevChatTransport } from "@/modules/programacion/ia-dev/chat/hooks/useIADevChatTransport";
import {
  createIADevTicket,
  type IADevAction,
} from "@/services/ia-dev.service";

const INITIAL_ASSISTANT_MESSAGE =
  "Agente IA listo. Describe tu consulta para continuar por chat.";

const createMessageId = (role: "user" | "assistant") =>
  `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const INITIAL_MESSAGES: ChatMessageModel[] = [
  {
    id: "assistant-initial",
    role: "assistant",
    content: INITIAL_ASSISTANT_MESSAGE,
    createdAt: 0,
    status: "final",
  },
];

const getVisibleActions = (actions: IADevAction[] | undefined) =>
  (actions ?? []).filter((action) => action.type !== "memory_review");

const AgenteIAModule = () => {
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const undoStackRef = useRef<string[]>([]);
  const redoStackRef = useRef<string[]>([]);
  const { pushPrompt, navigate, resetNavigation } = usePromptHistory();
  const {
    sendMessage,
    lastError: transportError,
  } = useIADevChatTransport();
  const {
    unreadCount,
    showScrollButton,
    notifyContentChanged,
    onScrollToBottomClick,
  } = useSmartAutoScroll({
    containerRef: chatScrollRef,
  });

  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<ChatMessageModel[]>(INITIAL_MESSAGES);
  const [messageWindowSize, setMessageWindowSize] = useState(80);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatStatus, setChatStatus] = useState("");
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null,
  );
  const [composerResetSignal, setComposerResetSignal] = useState(0);

  const visibleMessages = useMemo(
    () => messages.slice(-messageWindowSize),
    [messageWindowSize, messages],
  );
  const hasCollapsedMessages = messages.length > messageWindowSize;
  const effectiveChatStatus = useMemo(() => {
    if (transportError) {
      return "No fue posible conectar con el servicio en este momento.";
    }
    return chatStatus;
  }, [chatStatus, transportError]);

  const setChatInputTracked = (nextValue: string) => {
    setChatInput((prev) => {
      if (prev === nextValue) return prev;
      undoStackRef.current.push(prev);
      if (undoStackRef.current.length > 150) {
        undoStackRef.current.shift();
      }
      redoStackRef.current = [];
      return nextValue;
    });
  };

  const undoChatInput = () => {
    setChatInput((prev) => {
      if (undoStackRef.current.length === 0) return prev;
      const previous = undoStackRef.current.pop() ?? prev;
      redoStackRef.current.push(prev);
      return previous;
    });
  };

  const redoChatInput = () => {
    setChatInput((prev) => {
      if (redoStackRef.current.length === 0) return prev;
      const next = redoStackRef.current.pop() ?? prev;
      undoStackRef.current.push(prev);
      return next;
    });
  };

  const resetChatInputHistory = () => {
    undoStackRef.current = [];
    redoStackRef.current = [];
  };

  const appendAssistantMessage = (
    content: string,
    overrides?: Partial<ChatMessageModel>,
  ) => {
    setMessages((prev) => [
      ...prev,
      {
        id: createMessageId("assistant"),
        role: "assistant",
        content,
        createdAt: Date.now(),
        status: "final",
        ...overrides,
      },
    ]);
    notifyContentChanged("new-message", { behavior: "smooth" });
  };

  const submitChat = async () => {
    const value = chatInput.trim();
    if (!value || isSubmitting) return;

    const userMessageId = createMessageId("user");
    const assistantMessageId = createMessageId("assistant");

    setMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        role: "user",
        content: value,
        createdAt: Date.now(),
        status: "final",
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        createdAt: Date.now(),
        status: "streaming",
      },
    ]);
    setChatInput("");
    setComposerResetSignal((prev) => prev + 1);
    resetChatInputHistory();
    pushPrompt(value);
    resetNavigation();
    setStreamingMessageId(assistantMessageId);
    notifyContentChanged("user-submit", { behavior: "smooth", force: true });

    try {
      setIsSubmitting(true);
      const result = await sendMessage({
        message: value,
        sessionId: sessionId ?? undefined,
        callbacks: {
          onStart: () => {
            notifyContentChanged("stream-start", { behavior: "smooth" });
          },
          onChunk: (chunk) => {
            if (!chunk) return;
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      content: `${message.content}${chunk}`,
                      status: "streaming",
                    }
                  : message,
              ),
            );
            notifyContentChanged("stream-chunk", { behavior: "auto" });
          },
        },
      });

      setSessionId(result.session_id);
      const normalizedPayload = normalizeChatPayload(result);
      const visibleActions = getVisibleActions(result.actions);

      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content: result.reply || message.content,
                status: "final",
                normalized: normalizedPayload,
                actions: visibleActions,
              }
            : message,
        ),
      );
      setChatStatus("Respuesta generada correctamente.");
      notifyContentChanged("stream-end", { behavior: "smooth" });
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
            : "No fue posible procesar la consulta con Agente IA.";

      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                status: "error",
                content: `Error de integracion Agente IA: ${detail}`,
                error: detail,
              }
            : message,
        ),
      );
      setChatStatus("Error de conexion con IA DEV");
    } finally {
      setStreamingMessageId(null);
      setIsSubmitting(false);
    }
  };

  const handleActionClick = async (action: IADevAction) => {
    if (isSubmitting) return;
    if (action.type === "render_chart") {
      setChatStatus("La visualizacion ya se muestra integrada en la respuesta.");
      return;
    }
    if (action.type !== "create_ticket") return;

    const title = action.payload?.title?.trim() || "Solicitud desde Agente IA";
    const description =
      action.payload?.description?.trim() ||
      "Solicitud generada desde interaccion Agente IA.";
    const category = action.payload?.category?.trim() || "general";

    try {
      setIsSubmitting(true);
      const created = await createIADevTicket({
        session_id: sessionId ?? undefined,
        title,
        description,
        category,
      });

      appendAssistantMessage(
        `Ticket creado correctamente: ${created.ticket.ticket_id}. El equipo de desarrollo puede tomarlo desde ahora.`,
      );
      setChatStatus(`Ticket ${created.ticket.ticket_id} creado`);
    } catch {
      appendAssistantMessage("No fue posible crear el ticket en este momento.", {
        status: "error",
      });
      setChatStatus("Error al crear ticket");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full min-w-0 overflow-hidden">
      <PageBreadcrumb pageTitle={["Agente IA"]} />

      <div className="h-[calc(100vh-190px)] min-h-[680px] w-full min-w-0">
        <div className="mx-auto h-full min-w-0 max-w-6xl">
          <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/3">
            <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-4 py-3 dark:border-gray-800">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
                  <MessageSquare size={16} />
                  Agente Conversacional
                </div>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">
                  Modulo de chat para consultas analiticas con IA. Describe tu consulta y el agente te respondera con insights, visualizaciones y acciones recomendadas.
                </p>
              </div>
            </div>

            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-800">
              <div className="min-w-0">
                <p className="truncate text-sm text-gray-600 dark:text-gray-300">
                  {effectiveChatStatus || "Listo para consultas analiticas."}
                </p>
                {streamingMessageId && (
                  <p className="text-brand-600 dark:text-brand-300 mt-1 text-xs font-medium">
                    Agente escribiendo...
                  </p>
                )}
              </div>
            </div>

            <div className="relative min-h-0 flex-1">
              <div ref={chatScrollRef} className="h-full overflow-auto p-4">
                <div className="space-y-3">
                  {hasCollapsedMessages && (
                    <div className="flex justify-center">
                      <button
                        type="button"
                        onClick={() =>
                          setMessageWindowSize((prev) =>
                            Math.min(messages.length, prev + 80),
                          )
                        }
                        className="rounded-full border border-gray-300 bg-white px-3 py-1 text-xs font-semibold text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        Cargar mensajes anteriores (
                        {messages.length - visibleMessages.length})
                      </button>
                    </div>
                  )}

                  {visibleMessages.map((message) => (
                    <ChatMessageItem
                      key={message.id}
                      message={message}
                      isBusy={isSubmitting}
                      onActionClick={(action) => {
                        void handleActionClick(action);
                      }}
                    />
                  ))}
                </div>
              </div>

              {showScrollButton && (
                <ScrollToBottomButton
                  onClick={onScrollToBottomClick}
                  unreadCount={unreadCount}
                />
              )}
            </div>

            <ChatComposer
              value={chatInput}
              disabled={isSubmitting}
              isGenerating={Boolean(streamingMessageId)}
              resetSignal={composerResetSignal}
              onChange={setChatInputTracked}
              onSubmit={() => {
                void submitChat();
              }}
              onNavigateHistory={(direction) => {
                setChatInputTracked(navigate(direction, chatInput));
              }}
              onUndo={undoChatInput}
              onRedo={redoChatInput}
            />
          </section>
        </div>
      </div>
    </div>
  );
};

export default AgenteIAModule;
