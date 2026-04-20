"use client";

import { memo } from "react";
import { Bot } from "lucide-react";
import type { IADevAction } from "@/services/ia-dev.service";
import type { ChatMessageModel } from "@/modules/programacion/ia-dev/chat/types";
import ResponseRenderer from "@/modules/programacion/ia-dev/chat/components/ResponseRenderer";
import StreamingMessage from "@/modules/programacion/ia-dev/chat/components/StreamingMessage";

type AssistantMessageProps = {
  message: ChatMessageModel;
  onActionClick: (action: IADevAction) => void;
  isBusy: boolean;
};

const AssistantMessage = ({
  message,
  onActionClick,
  isBusy,
}: AssistantMessageProps) => {
  const visibleActions = (message.actions || []).filter(
    (action) => action.type !== "render_chart",
  );

  return (
    <article
      className={`shadow-theme-xs mr-auto max-w-[95%] rounded-2xl rounded-bl-md border px-4 py-3 text-sm ${
        message.status === "error"
          ? "border-red-200 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-950/35 dark:text-red-200"
          : "border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800/95 dark:text-gray-200"
      }`}
    >
      <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-wide uppercase opacity-80">
        <Bot size={12} />
        Asistente IA
      </div>

      <ResponseRenderer message={message} />

      {message.status === "streaming" && <StreamingMessage />}

      {message.pendingProposals && message.pendingProposals.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {message.pendingProposals.slice(0, 6).map((proposal) => (
            <span
              key={proposal.proposal_id}
              className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
              title={`${proposal.proposal_id} | ${proposal.status}`}
            >
              {proposal.status}
            </span>
          ))}
        </div>
      )}

      {message.memoryCandidates && message.memoryCandidates.length > 0 && (
        <div className="mt-3 rounded-lg border border-gray-200 bg-white/70 px-3 py-2 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-900/70 dark:text-gray-300">
          Candidatos de memoria detectados: {message.memoryCandidates.length}.
          Puedes revisarlos en el panel Memoria y Workflow.
        </div>
      )}

      {visibleActions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {visibleActions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => onActionClick(action)}
              className="border-brand-300 bg-brand-500/10 text-brand-700 hover:bg-brand-500/20 dark:border-brand-700 dark:text-brand-300 rounded-md border px-2 py-1 text-xs font-semibold transition disabled:opacity-60"
              disabled={isBusy}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </article>
  );
};

export default memo(AssistantMessage);
