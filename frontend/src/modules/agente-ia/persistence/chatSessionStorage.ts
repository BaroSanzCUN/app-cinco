"use client";

import type { ChatMessageModel } from "@/modules/programacion/ia-dev/chat/types";

export type AgenteIAChatThread = {
  id: string;
  title: string;
  sessionId: string | null;
  chatStatus: string;
  messageWindowSize: number;
  messages: ChatMessageModel[];
  createdAt: string;
  updatedAt: string;
};

export type AgenteIAChatHistoryState = {
  version: 2;
  activeChatId: string | null;
  chats: AgenteIAChatThread[];
  updatedAt: string;
};

type LegacyChatSessionState = {
  version: 1;
  sessionId: string | null;
  chatStatus: string;
  messageWindowSize: number;
  messages: ChatMessageModel[];
  updatedAt: string;
};

const CHAT_HISTORY_KEY = "agente-ia.chat-history.v2";
const LEGACY_CHAT_SESSION_KEY = "agente-ia.chat-session.v1";

const safeParse = <T>(raw: string | null): T | null => {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

const sanitizeMessage = (message: ChatMessageModel): ChatMessageModel => {
  if (message.status !== "streaming") return message;

  const interruptedContent =
    message.content.trim() ||
    "La respuesta anterior se interrumpio antes de completarse.";

  return {
    ...message,
    status: "error",
    content: interruptedContent,
    error: message.error || "Respuesta interrumpida por recarga o cierre.",
  };
};

const sanitizeMessages = (messages: ChatMessageModel[] | undefined) =>
  Array.isArray(messages) ? messages.map((message) => sanitizeMessage(message)) : [];

const buildThreadTitle = (messages: ChatMessageModel[]) => {
  const firstUserMessage = messages.find((message) => message.role === "user");
  if (!firstUserMessage) return "Nuevo chat";

  const compact = firstUserMessage.content.replace(/\s+/g, " ").trim();
  if (!compact) return "Nuevo chat";
  return compact.length > 52 ? `${compact.slice(0, 52)}...` : compact;
};

const sanitizeThread = (thread: AgenteIAChatThread): AgenteIAChatThread => {
  const messages = sanitizeMessages(thread.messages);
  const updatedAt =
    typeof thread.updatedAt === "string"
      ? thread.updatedAt
      : new Date().toISOString();

  return {
    id: thread.id,
    title: typeof thread.title === "string" && thread.title.trim()
      ? thread.title
      : buildThreadTitle(messages),
    sessionId: thread.sessionId ?? null,
    chatStatus: typeof thread.chatStatus === "string" ? thread.chatStatus : "",
    messageWindowSize:
      typeof thread.messageWindowSize === "number" ? thread.messageWindowSize : 80,
    messages,
    createdAt:
      typeof thread.createdAt === "string" ? thread.createdAt : updatedAt,
    updatedAt,
  };
};

const migrateLegacySession = (): AgenteIAChatHistoryState | null => {
  const legacySession = safeParse<LegacyChatSessionState>(
    window.sessionStorage.getItem(LEGACY_CHAT_SESSION_KEY),
  );

  if (!legacySession || legacySession.version !== 1) return null;

  const updatedAt =
    typeof legacySession.updatedAt === "string"
      ? legacySession.updatedAt
      : new Date().toISOString();

  const migratedThread = sanitizeThread({
    id: "chat-inicial",
    title: buildThreadTitle(sanitizeMessages(legacySession.messages)),
    sessionId: legacySession.sessionId ?? null,
    chatStatus:
      typeof legacySession.chatStatus === "string" ? legacySession.chatStatus : "",
    messageWindowSize:
      typeof legacySession.messageWindowSize === "number"
        ? legacySession.messageWindowSize
        : 80,
    messages: sanitizeMessages(legacySession.messages),
    createdAt: updatedAt,
    updatedAt,
  });

  window.sessionStorage.removeItem(LEGACY_CHAT_SESSION_KEY);

  return {
    version: 2,
    activeChatId: migratedThread.id,
    chats: [migratedThread],
    updatedAt,
  };
};

export const loadAgenteIAChatHistory = (): AgenteIAChatHistoryState | null => {
  if (typeof window === "undefined") return null;

  const parsed = safeParse<AgenteIAChatHistoryState>(
    window.localStorage.getItem(CHAT_HISTORY_KEY),
  );

  if (parsed && parsed.version === 2) {
    const chats = Array.isArray(parsed.chats)
      ? parsed.chats.map((chat) => sanitizeThread(chat))
      : [];

    return {
      version: 2,
      activeChatId: parsed.activeChatId ?? chats[0]?.id ?? null,
      chats,
      updatedAt:
        typeof parsed.updatedAt === "string"
          ? parsed.updatedAt
          : new Date().toISOString(),
    };
  }

  return migrateLegacySession();
};

export const saveAgenteIAChatHistory = (
  state: Omit<AgenteIAChatHistoryState, "version" | "updatedAt">,
) => {
  if (typeof window === "undefined") return;

  const payload: AgenteIAChatHistoryState = {
    version: 2,
    activeChatId: state.activeChatId,
    chats: state.chats.map((chat) => sanitizeThread(chat)),
    updatedAt: new Date().toISOString(),
  };

  window.localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(payload));
};

export const clearAgenteIAChatHistory = () => {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(CHAT_HISTORY_KEY);
  window.sessionStorage.removeItem(LEGACY_CHAT_SESSION_KEY);
};
