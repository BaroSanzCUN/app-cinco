import api from "@/lib/api";

const IA_DEV_CHAT_TIMEOUT_MS = 120000;

export type IADevChatRequest = {
  message: string;
  session_id?: string;
  reset_memory?: boolean;
};

export type IADevAction = {
  id: string;
  type: "create_ticket" | string;
  label: string;
  payload?: {
    category?: string;
    title?: string;
    description?: string;
  };
};

export type IADevChatResponse = {
  session_id: string;
  reply: string;
  orchestrator: {
    intent?: string;
    domain?: string;
    selected_agent?: string;
    classifier_source?: string;
    needs_database?: boolean;
    output_mode?: string;
    used_tools?: string[];
  };
  data: {
    kpis?: Record<string, number>;
    series?: unknown[];
    labels?: unknown[];
    insights?: string[];
  };
  data_sources?: {
    ai_dictionary?: {
      ok: boolean;
      table?: string | null;
      rows?: number;
      error?: string;
      snapshot?: {
        dictionary_table?: string;
        schema?: string;
        counts?: Record<string, number>;
      };
      context?: {
        domain?: {
          id?: number;
          code?: string;
          name?: string;
          description?: string;
          matched?: boolean;
        };
        tables?: Array<Record<string, unknown>>;
        fields?: Array<Record<string, unknown>>;
        rules?: Array<Record<string, unknown>>;
        relations?: Array<Record<string, unknown>>;
        synonyms?: Array<Record<string, unknown>>;
      };
    };
  };
  actions?: IADevAction[];
  trace: Array<{
    phase: string;
    status: string;
    at: string;
    detail: unknown;
    active_nodes?: string[];
  }>;
  memory: {
    used_messages: number;
    capacity_messages: number;
    usage_ratio: number;
    trim_events: number;
    saturated: boolean;
  };
  active_nodes?: string[];
};

export const sendIADevMessage = async (
  payload: IADevChatRequest,
): Promise<IADevChatResponse> => {
  const response = await api.post<IADevChatResponse>("/ia-dev/chat/", payload, {
    timeout: IA_DEV_CHAT_TIMEOUT_MS,
  });
  return response.data;
};

export const resetIADevMemory = async (sessionId: string) => {
  const response = await api.post("/ia-dev/memory/reset/", {
    session_id: sessionId,
  });
  return response.data;
};

export type IADevHealthResponse = {
  status: "ok" | "degraded";
  data_sources: {
    ai_dictionary: {
      ok: boolean;
      table?: string | null;
      rows?: number;
      error?: string;
      snapshot?: {
        dictionary_table?: string;
        schema?: string;
        counts?: Record<string, number>;
      };
    };
  };
};

export const getIADevHealth = async (): Promise<IADevHealthResponse> => {
  const response = await api.get<IADevHealthResponse>("/ia-dev/health/");
  return response.data;
};

export type IADevCreateTicketRequest = {
  session_id?: string;
  category?: string;
  title: string;
  description: string;
};

export type IADevCreateTicketResponse = {
  status: "created";
  ticket: {
    ticket_id: string;
    category: string;
    title: string;
    description: string;
    session_id?: string | null;
    created_at: number;
  };
};

export const createIADevTicket = async (
  payload: IADevCreateTicketRequest,
): Promise<IADevCreateTicketResponse> => {
  const response = await api.post<IADevCreateTicketResponse>(
    "/ia-dev/tickets/",
    payload,
  );
  return response.data;
};
