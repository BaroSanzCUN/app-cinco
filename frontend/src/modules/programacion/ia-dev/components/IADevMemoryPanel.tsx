"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCcw,
  X,
} from "lucide-react";
import {
  approveIADevMemoryProposal,
  createIADevMemoryProposal,
  listIADevMemoryAudit,
  listIADevMemoryProposals,
  listIADevUserMemory,
  rejectIADevMemoryProposal,
  setIADevUserMemory,
  type IADevAction,
  type IADevMemoryAuditEvent,
  type IADevMemoryCandidate,
  type IADevMemoryProposal,
  type IADevUserMemoryItem,
} from "@/services/ia-dev.service";

type MemoryTab = "candidates" | "proposals" | "user" | "audit";

type ProposalFilter = "all" | "pending" | "approved" | "rejected" | "applied";

type IADevMemoryPanelProps = {
  latestCandidates: IADevMemoryCandidate[];
  latestPendingProposals: IADevMemoryProposal[];
  latestActions: IADevAction[];
  isBusy: boolean;
  onStatusChange?: (message: string) => void;
};

const formatDateTime = (value?: number | null) => {
  if (!value) return "-";
  return new Date(value * 1000).toLocaleString("es-CO");
};

const asShortJson = (value: unknown) => {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

const scopeBadgeClass = (scope: string) => {
  const normalized = scope.toLowerCase();
  if (normalized === "user") {
    return "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
  }
  if (normalized === "business") {
    return "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  }
  if (normalized === "general") {
    return "border-violet-300 bg-violet-50 text-violet-700 dark:border-violet-700 dark:bg-violet-900/30 dark:text-violet-300";
  }
  return "border-gray-300 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300";
};

const statusBadgeClass = (status: string) => {
  const normalized = status.toLowerCase();
  if (normalized === "pending") {
    return "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  }
  if (normalized === "approved") {
    return "border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-900/30 dark:text-sky-300";
  }
  if (normalized === "applied") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  }
  if (normalized === "rejected") {
    return "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300";
  }
  return "border-gray-300 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300";
};

const getCandidateId = (candidate: IADevMemoryCandidate) => {
  return (
    candidate.proposal_id ||
    `${candidate.scope}:${candidate.candidate_key}:${asShortJson(candidate.candidate_value)}`
  );
};

const IADevMemoryPanel = ({
  latestCandidates,
  latestPendingProposals,
  latestActions,
  isBusy,
  onStatusChange,
}: IADevMemoryPanelProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<MemoryTab>("candidates");
  const [proposalFilter, setProposalFilter] = useState<ProposalFilter>("pending");
  const [auditScope, setAuditScope] = useState("user");
  const [ignoredCandidateIds, setIgnoredCandidateIds] = useState<Set<string>>(new Set());
  const [proposals, setProposals] = useState<IADevMemoryProposal[]>([]);
  const [userMemory, setUserMemory] = useState<IADevUserMemoryItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<IADevMemoryAuditEvent[]>([]);
  const [loadingTab, setLoadingTab] = useState<MemoryTab | null>(null);
  const [processingKey, setProcessingKey] = useState<string | null>(null);
  const [panelError, setPanelError] = useState<string>("");
  const [isLoadedByTab, setIsLoadedByTab] = useState<Record<MemoryTab, boolean>>({
    candidates: true,
    proposals: false,
    user: false,
    audit: false,
  });

  const memoryReviewActions = useMemo(
    () => latestActions.filter((item) => String(item.type || "").startsWith("memory_")),
    [latestActions],
  );

  useEffect(() => {
    if (latestPendingProposals.length > 0) {
      setProposals(latestPendingProposals);
      setIsOpen(true);
      setActiveTab("proposals");
      setIsLoadedByTab((prev) => ({ ...prev, proposals: true }));
    }
  }, [latestPendingProposals]);

  useEffect(() => {
    if (latestCandidates.length > 0 && !isOpen) {
      setIsOpen(true);
    }
  }, [latestCandidates, isOpen]);

  useEffect(() => {
    if (memoryReviewActions.length > 0) {
      setIsOpen(true);
      setActiveTab("proposals");
    }
  }, [memoryReviewActions.length]);

  const reportStatus = useCallback(
    (message: string) => {
      setPanelError("");
      onStatusChange?.(message);
    },
    [onStatusChange],
  );

  const reportError = useCallback(
    (message: string) => {
      setPanelError(message);
      onStatusChange?.(message);
    },
    [onStatusChange],
  );

  const loadProposals = useCallback(async () => {
    setLoadingTab("proposals");
    setPanelError("");
    try {
      const response = await listIADevMemoryProposals({
        status: proposalFilter === "all" ? undefined : proposalFilter,
        limit: 50,
      });
      setProposals(response.proposals ?? []);
      setIsLoadedByTab((prev) => ({ ...prev, proposals: true }));
    } catch {
      reportError("No se pudo cargar propuestas de memoria.");
    } finally {
      setLoadingTab(null);
    }
  }, [proposalFilter, reportError]);

  const loadUserMemory = useCallback(async () => {
    setLoadingTab("user");
    setPanelError("");
    try {
      const response = await listIADevUserMemory({ limit: 60 });
      setUserMemory(response.memory ?? []);
      setIsLoadedByTab((prev) => ({ ...prev, user: true }));
    } catch {
      reportError("No se pudo cargar la memoria de usuario.");
    } finally {
      setLoadingTab(null);
    }
  }, [reportError]);

  const loadAudit = useCallback(async () => {
    setLoadingTab("audit");
    setPanelError("");
    try {
      const response = await listIADevMemoryAudit({
        scope: auditScope,
        limit: 60,
      });
      setAuditEvents(response.events ?? []);
      setIsLoadedByTab((prev) => ({ ...prev, audit: true }));
    } catch {
      reportError(
        auditScope === "user"
          ? "No se pudo cargar auditoria de memoria."
          : "No autorizado o sin acceso para auditoria global.",
      );
    } finally {
      setLoadingTab(null);
    }
  }, [auditScope, reportError]);

  useEffect(() => {
    if (!isOpen) return;
    if (activeTab === "proposals" && !isLoadedByTab.proposals) {
      void loadProposals();
    }
    if (activeTab === "user" && !isLoadedByTab.user) {
      void loadUserMemory();
    }
    if (activeTab === "audit" && !isLoadedByTab.audit) {
      void loadAudit();
    }
  }, [activeTab, isLoadedByTab, isOpen, loadAudit, loadProposals, loadUserMemory]);

  useEffect(() => {
    if (!isOpen || activeTab !== "proposals") return;
    if (isLoadedByTab.proposals) {
      void loadProposals();
    }
  }, [proposalFilter, activeTab, isOpen, isLoadedByTab.proposals, loadProposals]);

  useEffect(() => {
    if (!isOpen || activeTab !== "audit") return;
    if (isLoadedByTab.audit) {
      void loadAudit();
    }
  }, [auditScope, activeTab, isOpen, isLoadedByTab.audit, loadAudit]);

  const candidates = useMemo(() => {
    return latestCandidates.filter((candidate) => !ignoredCandidateIds.has(getCandidateId(candidate)));
  }, [ignoredCandidateIds, latestCandidates]);

  const persistCandidateAsPreference = async (candidate: IADevMemoryCandidate) => {
    const candidateId = getCandidateId(candidate);
    if (!candidate.candidate_key) return;
    try {
      setProcessingKey(candidateId);
      const result = await setIADevUserMemory({
        memory_key: candidate.candidate_key,
        memory_value: candidate.candidate_value ?? null,
        sensitivity: (candidate.sensitivity as "low" | "medium" | "high") || "low",
      });
      if (!result.ok) {
        reportError(result.error || "No se pudo guardar preferencia.");
        return;
      }
      setIgnoredCandidateIds((prev) => new Set(prev).add(candidateId));
      reportStatus(`Preferencia guardada: ${candidate.candidate_key}`);
      if (isLoadedByTab.user) {
        await loadUserMemory();
      }
      if (isLoadedByTab.audit) {
        await loadAudit();
      }
    } catch {
      reportError("No se pudo guardar preferencia.");
    } finally {
      setProcessingKey(null);
    }
  };

  const proposeCandidateAsRule = async (candidate: IADevMemoryCandidate) => {
    const candidateId = getCandidateId(candidate);
    if (!candidate.candidate_key) return;
    try {
      setProcessingKey(candidateId);
      const scope =
        candidate.scope === "business" || candidate.scope === "general"
          ? candidate.scope
          : "business";
      const result = await createIADevMemoryProposal({
        scope,
        candidate_key: candidate.candidate_key,
        candidate_value: candidate.candidate_value ?? null,
        reason: candidate.reason || "Propuesta creada desde IA DEV Workspace",
        sensitivity:
          (candidate.sensitivity as "low" | "medium" | "high") || "medium",
        domain_code: undefined,
        capability_id: undefined,
      });
      if (!result.ok) {
        reportError(result.error || "No se pudo crear propuesta.");
        return;
      }
      setIgnoredCandidateIds((prev) => new Set(prev).add(candidateId));
      reportStatus(
        result.proposal?.proposal_id
          ? `Propuesta creada: ${result.proposal.proposal_id}`
          : "Propuesta creada",
      );
      setActiveTab("proposals");
      await loadProposals();
      if (isLoadedByTab.audit) {
        await loadAudit();
      }
    } catch {
      reportError("No se pudo proponer como regla.");
    } finally {
      setProcessingKey(null);
    }
  };

  const ignoreCandidate = (candidate: IADevMemoryCandidate) => {
    setIgnoredCandidateIds((prev) => new Set(prev).add(getCandidateId(candidate)));
    reportStatus(`Candidato ignorado: ${candidate.candidate_key}`);
  };

  const approveProposal = async (proposalId: string) => {
    try {
      setProcessingKey(proposalId);
      const result = await approveIADevMemoryProposal({ proposal_id: proposalId });
      if (!result.ok) {
        reportError(result.error || "No se pudo aprobar la propuesta.");
        return;
      }
      reportStatus(`Propuesta aprobada: ${proposalId}`);
      await loadProposals();
      if (isLoadedByTab.audit) {
        await loadAudit();
      }
      if (isLoadedByTab.user) {
        await loadUserMemory();
      }
    } catch {
      reportError("No se pudo aprobar la propuesta.");
    } finally {
      setProcessingKey(null);
    }
  };

  const rejectProposal = async (proposalId: string) => {
    try {
      setProcessingKey(proposalId);
      const result = await rejectIADevMemoryProposal({ proposal_id: proposalId });
      if (!result.ok) {
        reportError(result.error || "No se pudo rechazar la propuesta.");
        return;
      }
      reportStatus(`Propuesta rechazada: ${proposalId}`);
      await loadProposals();
      if (isLoadedByTab.audit) {
        await loadAudit();
      }
    } catch {
      reportError("No se pudo rechazar la propuesta.");
    } finally {
      setProcessingKey(null);
    }
  };

  const onRefreshCurrentTab = async () => {
    if (activeTab === "proposals") {
      await loadProposals();
      return;
    }
    if (activeTab === "user") {
      await loadUserMemory();
      return;
    }
    if (activeTab === "audit") {
      await loadAudit();
      return;
    }
  };

  const loadingCurrentTab = loadingTab === activeTab;

  return (
    <div className="border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between px-3 py-2">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          Memoria y Workflow
          {latestPendingProposals.length > 0 && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700 dark:bg-amber-900/40 dark:text-amber-200">
              {latestPendingProposals.length} pendientes
            </span>
          )}
        </button>
        {isOpen && (
          <button
            type="button"
            onClick={() => {
              void onRefreshCurrentTab();
            }}
            className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            disabled={loadingCurrentTab}
          >
            {loadingCurrentTab ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <RefreshCcw size={12} />
            )}
            Refresh
          </button>
        )}
      </div>

      {isOpen && (
        <div className="space-y-3 px-3 pb-3">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["candidates", "Candidatos"],
                ["proposals", "Propuestas"],
                ["user", "Memoria usuario"],
                ["audit", "Auditoria"],
              ] as const
            ).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-md border px-2 py-1 text-xs font-medium ${
                  activeTab === tab
                    ? "border-brand-500 bg-brand-500/10 text-brand-700 dark:border-brand-500 dark:text-brand-300"
                    : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {panelError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700 dark:border-red-700 dark:bg-red-900/20 dark:text-red-300">
              {panelError}
            </div>
          )}

          {activeTab === "candidates" && (
            <div className="max-h-56 space-y-2 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
              {candidates.length === 0 ? (
                <p className="text-xs text-gray-500 dark:text-gray-300">
                  No hay candidatos de memoria detectados en este momento.
                </p>
              ) : (
                candidates.map((candidate) => {
                  const candidateId = getCandidateId(candidate);
                  const isCandidateBusy = processingKey === candidateId || isBusy;
                  return (
                    <div
                      key={candidateId}
                      className="rounded-md border border-gray-200 bg-white p-2 text-xs dark:border-gray-700 dark:bg-gray-900"
                    >
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <p className="truncate font-semibold text-gray-700 dark:text-gray-200">
                          {candidate.candidate_key}
                        </p>
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${scopeBadgeClass(candidate.scope)}`}
                        >
                          {candidate.scope}
                        </span>
                      </div>
                      <p className="mb-1 text-gray-500 dark:text-gray-300">
                        {candidate.reason || "Sin razon especifica"}
                      </p>
                      <p className="mb-2 line-clamp-2 text-gray-500 dark:text-gray-300">
                        Valor: {asShortJson(candidate.candidate_value)}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            void persistCandidateAsPreference(candidate);
                          }}
                          disabled={isCandidateBusy}
                          className="rounded-md border border-emerald-300 bg-emerald-50 px-2 py-1 font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                        >
                          Guardar preferencia
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            void proposeCandidateAsRule(candidate);
                          }}
                          disabled={isCandidateBusy || Boolean(candidate.proposal_id)}
                          className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-50 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                        >
                          {candidate.proposal_id ? "Ya propuesta" : "Proponer como regla"}
                        </button>
                        <button
                          type="button"
                          onClick={() => ignoreCandidate(candidate)}
                          disabled={isCandidateBusy}
                          className="rounded-md border border-gray-300 bg-gray-50 px-2 py-1 font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
                        >
                          Ignorar
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {activeTab === "proposals" && (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {(["all", "pending", "approved", "rejected", "applied"] as const).map(
                  (status) => (
                    <button
                      key={status}
                      type="button"
                      onClick={() => setProposalFilter(status)}
                      className={`rounded-md border px-2 py-1 text-[11px] font-medium ${
                        proposalFilter === status
                          ? "border-brand-500 bg-brand-500/10 text-brand-700 dark:border-brand-500 dark:text-brand-300"
                          : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                      }`}
                    >
                      {status}
                    </button>
                  ),
                )}
              </div>
              <div className="max-h-56 space-y-2 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                {proposals.length === 0 ? (
                  <p className="text-xs text-gray-500 dark:text-gray-300">
                    No hay propuestas para el filtro seleccionado.
                  </p>
                ) : (
                  proposals.map((proposal) => {
                    const isProposalBusy = processingKey === proposal.proposal_id || isBusy;
                    const proposalStatus = String(proposal.status || "pending");
                    return (
                      <div
                        key={proposal.proposal_id}
                        className="rounded-md border border-gray-200 bg-white p-2 text-xs dark:border-gray-700 dark:bg-gray-900"
                      >
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <p className="truncate font-semibold text-gray-700 dark:text-gray-200">
                            {proposal.candidate_key}
                          </p>
                          <span
                            className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusBadgeClass(proposalStatus)}`}
                          >
                            {proposalStatus}
                          </span>
                        </div>
                        <p className="mb-1 text-gray-500 dark:text-gray-300">
                          {proposal.proposal_id} - {proposal.scope}
                        </p>
                        <p className="mb-2 line-clamp-2 text-gray-500 dark:text-gray-300">
                          {proposal.reason || "Sin razon"}
                        </p>
                        <div className="mb-2 text-[11px] text-gray-500 dark:text-gray-300">
                          Actualizada: {formatDateTime(proposal.updated_at)}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              void approveProposal(proposal.proposal_id);
                            }}
                            disabled={isProposalBusy || proposalStatus !== "pending"}
                            className="inline-flex items-center gap-1 rounded-md border border-emerald-300 bg-emerald-50 px-2 py-1 font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
                          >
                            <Check size={12} />
                            Aprobar
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              void rejectProposal(proposal.proposal_id);
                            }}
                            disabled={isProposalBusy || proposalStatus !== "pending"}
                            className="inline-flex items-center gap-1 rounded-md border border-red-300 bg-red-50 px-2 py-1 font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50 dark:border-red-700 dark:bg-red-900/20 dark:text-red-300"
                          >
                            <X size={12} />
                            Rechazar
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {activeTab === "user" && (
            <div className="max-h-56 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
              {userMemory.length === 0 ? (
                <p className="text-xs text-gray-500 dark:text-gray-300">
                  No hay memoria de usuario registrada.
                </p>
              ) : (
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-gray-500 dark:text-gray-300">
                      <th className="pb-1">Key</th>
                      <th className="pb-1">Valor</th>
                      <th className="pb-1">Nivel</th>
                      <th className="pb-1">Actualizado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {userMemory.map((item) => (
                      <tr key={`${item.id}-${item.memory_key}`} className="align-top text-gray-700 dark:text-gray-200">
                        <td className="pr-2 pb-1 font-medium">{item.memory_key}</td>
                        <td className="pr-2 pb-1">{asShortJson(item.memory_value)}</td>
                        <td className="pr-2 pb-1">{item.sensitivity}</td>
                        <td className="pb-1">{formatDateTime(item.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {activeTab === "audit" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-600 dark:text-gray-300">
                  Scope:
                </label>
                <select
                  value={auditScope}
                  onChange={(event) => setAuditScope(event.target.value)}
                  className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                >
                  <option value="user">user</option>
                  <option value="business">business</option>
                  <option value="general">general</option>
                </select>
              </div>
              <div className="max-h-56 overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                {auditEvents.length === 0 ? (
                  <p className="text-xs text-gray-500 dark:text-gray-300">
                    Sin eventos de auditoria para el filtro actual.
                  </p>
                ) : (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-gray-500 dark:text-gray-300">
                        <th className="pb-1">Cuando</th>
                        <th className="pb-1">Actor</th>
                        <th className="pb-1">Accion</th>
                        <th className="pb-1">Entidad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditEvents.map((event) => (
                        <tr key={event.id} className="align-top text-gray-700 dark:text-gray-200">
                          <td className="pr-2 pb-1">{formatDateTime(event.created_at)}</td>
                          <td className="pr-2 pb-1">{event.actor_key}</td>
                          <td className="pr-2 pb-1">{event.action}</td>
                          <td className="pb-1">{event.entity_key}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IADevMemoryPanel;


