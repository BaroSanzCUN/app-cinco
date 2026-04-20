import { useCallback, useRef, useState } from "react";

const MAX_PROMPT_HISTORY = 80;

export const usePromptHistory = () => {
  const [history, setHistory] = useState<string[]>([]);
  const navigationIndexRef = useRef(-1);
  const draftRef = useRef("");

  const pushPrompt = useCallback((prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed) return;

    setHistory((prev) => {
      if (prev[prev.length - 1] === trimmed) {
        return prev;
      }
      const next = [...prev, trimmed];
      return next.slice(-MAX_PROMPT_HISTORY);
    });

    navigationIndexRef.current = -1;
    draftRef.current = "";
  }, []);

  const resetNavigation = useCallback(() => {
    navigationIndexRef.current = -1;
    draftRef.current = "";
  }, []);

  const navigate = useCallback(
    (direction: "up" | "down", currentDraft: string): string => {
      if (history.length === 0) return currentDraft;

      const currentIndex = navigationIndexRef.current;
      if (currentIndex === -1) {
        draftRef.current = currentDraft;
      }

      if (direction === "up") {
        const nextIndex =
          currentIndex === -1
            ? history.length - 1
            : Math.max(0, currentIndex - 1);
        navigationIndexRef.current = nextIndex;
        return history[nextIndex] || currentDraft;
      }

      if (currentIndex >= history.length - 1 || currentIndex === -1) {
        navigationIndexRef.current = -1;
        return draftRef.current;
      }

      const nextIndex = Math.min(history.length - 1, currentIndex + 1);
      navigationIndexRef.current = nextIndex;
      return history[nextIndex] || draftRef.current;
    },
    [history],
  );

  return {
    history,
    pushPrompt,
    navigate,
    resetNavigation,
  };
};
