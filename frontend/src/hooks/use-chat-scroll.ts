import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { STREAMING_SCROLL_THRESHOLD } from "@/features/chat";

interface UseChatScrollOptions {
  messageCount: number;
  isStreaming: boolean;
  streamDependency?: string | number;
  threshold?: number;
}

interface UseChatScrollResult {
  containerRef: RefObject<HTMLDivElement>;
  bottomAnchorRef: RefObject<HTMLDivElement>;
  isAtBottom: boolean;
  scrollToBottom: (behavior?: ScrollBehavior) => void;
}

function isNearBottom(element: HTMLDivElement, threshold: number): boolean {
  const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
  return distanceFromBottom <= threshold;
}

export function useChatScroll({
  messageCount,
  isStreaming,
  streamDependency,
  threshold = STREAMING_SCROLL_THRESHOLD
}: UseChatScrollOptions): UseChatScrollResult {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomAnchorRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const isAtBottomRef = useRef(true);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    bottomAnchorRef.current?.scrollIntoView({
      behavior,
      block: "end",
      inline: "nearest"
    });
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onScroll = () => {
      const nextIsAtBottom = isNearBottom(container, threshold);
      isAtBottomRef.current = nextIsAtBottom;
      setIsAtBottom((previous) => (previous === nextIsAtBottom ? previous : nextIsAtBottom));
    };

    onScroll();
    container.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      container.removeEventListener("scroll", onScroll);
    };
  }, [threshold]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const shouldFollow =
      isAtBottomRef.current || (isStreaming && isNearBottom(container, Math.max(threshold, threshold * 1.5)));

    if (!shouldFollow) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      scrollToBottom("auto");
    });

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [isStreaming, messageCount, scrollToBottom, streamDependency, threshold]);

  return {
    containerRef,
    bottomAnchorRef,
    isAtBottom,
    scrollToBottom
  };
}
