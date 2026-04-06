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
    backend?: string;
    redis_enabled?: boolean;
  };
  observability?: {
    enabled: boolean;
    duration_ms: number;
    tool_latencies_ms: Record<string, number>;
    tokens_in: number;
    tokens_out: number;
    estimated_cost_usd: number;
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

export type IADevKnowledgeProposal = {
  proposal_id: string;
  status: string;
  mode: "ceo" | "auto" | "directo" | string;
  proposal_type: "nueva_regla" | "actualizacion_regla" | string;
  name: string;
  description: string;
  domain_code: string;
  condition_sql: string;
  result_text: string;
  tables_related: string;
  priority: number;
  target_rule_id?: number | null;
  session_id?: string | null;
  requested_by: string;
  similar_rules: Array<Record<string, unknown>>;
  created_at: number;
  updated_at: number;
  persistence?: Record<string, unknown> | null;
  error?: string | null;
};

export type IADevKnowledgeProposalCreateRequest = {
  message?: string;
  session_id?: string;
  requested_by?: string;
  proposal_type?: "nueva_regla" | "actualizacion_regla";
  name?: string;
  description?: string;
  domain_code?: string;
  condition_sql?: string;
  result_text?: string;
  tables_related?: string;
  priority?: number;
  target_rule_id?: number;
};

export type IADevKnowledgeProposalCreateResponse = {
  ok: boolean;
  requires_auth?: boolean;
  applied?: boolean;
  proposal?: IADevKnowledgeProposal;
  apply_result?: Record<string, unknown>;
  error?: string;
};

export type IADevKnowledgeProposalListResponse = {
  status: "ok";
  count: number;
  proposals: IADevKnowledgeProposal[];
};

export type IADevKnowledgeApproveRequest = {
  proposal_id: string;
  auth_key?: string;
  idempotency_key?: string;
};

export type IADevKnowledgeApproveResponse = {
  ok: boolean;
  status?: "accepted";
  async_mode?: string;
  job?: {
    job_id: string;
    job_type: string;
    status: string;
    payload?: Record<string, unknown>;
    result?: Record<string, unknown> | null;
    error?: string | null;
    idempotency_key?: string | null;
    created_at?: number;
    updated_at?: number;
    run_after?: number;
  };
  proposal?: IADevKnowledgeProposal;
  persistence?: Record<string, unknown>;
  error?: string;
  requires_auth?: boolean;
};

export type IADevKnowledgeRejectRequest = {
  proposal_id: string;
  reason?: string;
};

export const createIADevKnowledgeProposal = async (
  payload: IADevKnowledgeProposalCreateRequest,
): Promise<IADevKnowledgeProposalCreateResponse> => {
  const response = await api.post<IADevKnowledgeProposalCreateResponse>(
    "/ia-dev/knowledge/proposals/",
    payload,
  );
  return response.data;
};

export const listIADevKnowledgeProposals = async (
  params?: { status?: string; limit?: number },
): Promise<IADevKnowledgeProposalListResponse> => {
  const response = await api.get<IADevKnowledgeProposalListResponse>(
    "/ia-dev/knowledge/proposals/",
    { params },
  );
  return response.data;
};

export const approveIADevKnowledgeProposal = async (
  payload: IADevKnowledgeApproveRequest,
): Promise<IADevKnowledgeApproveResponse> => {
  const response = await api.post<IADevKnowledgeApproveResponse>(
    "/ia-dev/knowledge/proposals/approve/",
    payload,
  );
  return response.data;
};

export const rejectIADevKnowledgeProposal = async (
  payload: IADevKnowledgeRejectRequest,
): Promise<IADevKnowledgeApproveResponse> => {
  const response = await api.post<IADevKnowledgeApproveResponse>(
    "/ia-dev/knowledge/proposals/reject/",
    payload,
  );
  return response.data;
};

export type IADevAsyncJobStatusResponse = {
  status: "ok";
  job: {
    job_id: string;
    job_type: string;
    status: "pending" | "running" | "done" | "failed" | string;
    payload?: Record<string, unknown>;
    result?: Record<string, unknown> | null;
    error?: string | null;
    idempotency_key?: string | null;
    created_at?: number;
    updated_at?: number;
    run_after?: number;
  };
};

export const getIADevAsyncJobStatus = async (
  jobId: string,
): Promise<IADevAsyncJobStatusResponse> => {
  const response = await api.get<IADevAsyncJobStatusResponse>(
    "/ia-dev/async/jobs/",
    { params: { job_id: jobId } },
  );
  return response.data;
};

export type IADevObservabilitySummaryResponse = {
  status: "ok";
  observability: {
    enabled: boolean;
    window_seconds: number;
    sample_size: number;
    event_types: Record<string, number>;
    totals: {
      events: number;
      tokens_in: number;
      tokens_out: number;
      cost_usd: number;
      latency: {
        count: number;
        avg_ms: number;
        p95_ms: number;
        max_ms: number;
      };
    };
    sources: Record<
      string,
      {
        events: number;
        tokens_in: number;
        tokens_out: number;
        cost_usd: number;
        latency: {
          count: number;
          avg_ms: number;
          p95_ms: number;
          max_ms: number;
        };
      }
    >;
  };
};

export const getIADevObservabilitySummary = async (
  params?: { window_seconds?: number; limit?: number },
): Promise<IADevObservabilitySummaryResponse> => {
  const response = await api.get<IADevObservabilitySummaryResponse>(
    "/ia-dev/observability/summary/",
    { params },
  );
  return response.data;
};

export type IADevAttendancePeriodResolveResponse = {
  status: "ok";
  period_resolution: {
    session_id: string;
    input: {
      message: string;
      explicit_period_detected: boolean;
    };
    resolved_period: {
      label: string;
      source: string;
      start_date: string | null;
      end_date: string | null;
      confidence?: number;
    };
    rules_fallback_period: {
      label: string;
      source: string;
      start_date: string | null;
      end_date: string | null;
    };
    alternative_hint?: string | null;
  };
};

export const resolveIADevAttendancePeriod = async (payload: {
  message: string;
  session_id?: string;
}): Promise<IADevAttendancePeriodResolveResponse> => {
  const response = await api.post<IADevAttendancePeriodResolveResponse>(
    "/ia-dev/attendance/period/resolve/",
    payload,
  );
  return response.data;
};
