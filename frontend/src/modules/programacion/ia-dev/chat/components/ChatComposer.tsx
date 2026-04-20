"use client";

import { Loader2, SendHorizonal } from "lucide-react";
import type { KeyboardEvent } from "react";
import ResizableComposer from "@/modules/programacion/ia-dev/chat/components/ResizableComposer";

type ChatComposerProps = {
  value: string;
  disabled?: boolean;
  isGenerating?: boolean;
  resetSignal?: number;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onNavigateHistory: (direction: "up" | "down") => void;
  onUndo: () => void;
  onRedo: () => void;
};

const ChatComposer = ({
  value,
  disabled = false,
  isGenerating = false,
  resetSignal = 0,
  onChange,
  onSubmit,
  onNavigateHistory,
  onUndo,
  onRedo,
}: ChatComposerProps) => {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    const isModifier = event.ctrlKey || event.metaKey;
    const target = event.currentTarget;
    const isEnter = event.key === "Enter";
    const isArrowUp = event.key === "ArrowUp";
    const isArrowDown = event.key === "ArrowDown";
    const key = event.key.toLowerCase();

    if (isModifier && key === "z" && !event.shiftKey) {
      event.preventDefault();
      onUndo();
      return;
    }

    if (isModifier && (key === "y" || (key === "z" && event.shiftKey))) {
      event.preventDefault();
      onRedo();
      return;
    }

    if (isEnter && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
      return;
    }

    if (
      isArrowUp &&
      !event.shiftKey &&
      !event.altKey &&
      target.selectionStart === 0 &&
      target.selectionEnd === 0
    ) {
      event.preventDefault();
      onNavigateHistory("up");
      return;
    }

    if (
      isArrowDown &&
      !event.shiftKey &&
      !event.altKey &&
      target.selectionStart === target.value.length &&
      target.selectionEnd === target.value.length
    ) {
      event.preventDefault();
      onNavigateHistory("down");
    }
  };

  return (
    <div className="border-t border-gray-200 bg-gray-50/70 p-3 dark:border-gray-800 dark:bg-gray-900/60">
      <div className="flex items-end gap-2">
        <ResizableComposer
          key={`composer-${resetSignal}`}
          value={value}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          minHeight={72}
          maxHeight={520}
        />
        <button
          type="button"
          onClick={onSubmit}
          className="bg-brand-500 shadow-theme-sm hover:bg-brand-600 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white transition disabled:cursor-not-allowed disabled:opacity-70"
          title="Enviar mensaje"
          disabled={disabled}
        >
          {isGenerating ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <SendHorizonal size={16} />
          )}
        </button>
      </div>
      <p className="mt-2 px-1 text-[11px] text-gray-500 dark:text-gray-400">
        Enter para enviar, Shift+Enter para salto de linea, flechas arriba/abajo
        para historial.
      </p>
    </div>
  );
};

export default ChatComposer;
