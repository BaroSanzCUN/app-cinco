import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

type ContentChangeReason =
  | "user-submit"
  | "stream-start"
  | "stream-chunk"
  | "stream-end"
  | "new-message";

type UseSmartAutoScrollParams = {
  containerRef: RefObject<HTMLDivElement | null>;
  bottomThreshold?: number;
};

type NotifyOptions = {
  behavior?: ScrollBehavior;
  force?: boolean;
};

const isNearBottom = (
  container: HTMLDivElement,
  threshold: number,
): boolean => {
  const distance =
    container.scrollHeight - container.scrollTop - container.clientHeight;
  return distance <= threshold;
};

export const useSmartAutoScroll = ({
  containerRef,
  bottomThreshold = 120,
}: UseSmartAutoScrollParams) => {
  const atBottomRef = useRef(true);
  const unreadRef = useRef(0);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const container = containerRef.current;
      if (!container) return;
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });
    },
    [containerRef],
  );

  const notifyContentChanged = useCallback(
    (_reason: ContentChangeReason, options?: NotifyOptions) => {
      const container = containerRef.current;
      if (!container) return;

      const shouldForce = Boolean(options?.force);
      const shouldStick = atBottomRef.current || shouldForce;
      if (shouldStick) {
        scrollToBottom(options?.behavior || "smooth");
        unreadRef.current = 0;
        setUnreadCount(0);
        return;
      }

      unreadRef.current += 1;
      setUnreadCount(unreadRef.current);
    },
    [containerRef, scrollToBottom],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const nearBottom = isNearBottom(container, bottomThreshold);
      atBottomRef.current = nearBottom;
      setIsAtBottom(nearBottom);

      if (nearBottom && unreadRef.current > 0) {
        unreadRef.current = 0;
        setUnreadCount(0);
      }
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, [bottomThreshold, containerRef]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;

    let rafId = 0;
    const observer = new ResizeObserver(() => {
      if (!atBottomRef.current) return;
      cancelAnimationFrame(rafId);
      rafId = window.requestAnimationFrame(() => {
        scrollToBottom("auto");
      });
    });

    observer.observe(container);
    return () => {
      cancelAnimationFrame(rafId);
      observer.disconnect();
    };
  }, [containerRef, scrollToBottom]);

  const showScrollButton = useMemo(
    () => !isAtBottom && unreadCount > 0,
    [isAtBottom, unreadCount],
  );

  const onScrollToBottomClick = useCallback(() => {
    unreadRef.current = 0;
    setUnreadCount(0);
    scrollToBottom("smooth");
  }, [scrollToBottom]);

  return {
    isAtBottom,
    unreadCount,
    showScrollButton,
    notifyContentChanged,
    scrollToBottom,
    onScrollToBottomClick,
  };
};
