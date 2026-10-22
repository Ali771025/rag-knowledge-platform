import { useMemo } from "react";
import { useMessageStreamingStore } from "@/state";
import { useUiStore } from "@/state";
import { isMessageStreamActiveState } from "@/features/chat";

export interface UseMessageStreamingResult {
  lifecycle: ReturnType<typeof useMessageStreamingStore.getState>["lifecycle"];
  activeMessageId: string | null;
  isStreaming: boolean;
  isPaused: boolean;
  isTerminal: boolean;
  hasError: boolean;
  startedAt: string | null;
  completedAt: string | null;
  lastChunkAt: string | null;
  errorMessage: string | null;
}

export function useMessageStreaming(): UseMessageStreamingResult {
  const lifecycle = useMessageStreamingStore((state) => state.lifecycle);
  const activeMessageId = useMessageStreamingStore((state) => state.activeMessageId);
  const startedAt = useMessageStreamingStore((state) => state.streamStartedAt);
  const completedAt = useMessageStreamingStore((state) => state.streamCompletedAt);
  const lastChunkAt = useMessageStreamingStore((state) => state.lastChunkAt);
  const errorMessage = useMessageStreamingStore((state) => state.errorMessage);
  const uiStreaming = useUiStore((state) => state.isStreaming);

  return useMemo(() => {
    const isActive = isMessageStreamActiveState(lifecycle);
    const isTerminal = lifecycle === "completed" || lifecycle === "interrupted" || lifecycle === "failed";
    const isPaused = lifecycle === "paused";
    const hasError = lifecycle === "failed";

    return {
      lifecycle,
      activeMessageId,
      isStreaming: uiStreaming || isActive,
      isPaused,
      isTerminal,
      hasError,
      startedAt,
      completedAt,
      lastChunkAt,
      errorMessage
    };
  }, [activeMessageId, completedAt, errorMessage, lastChunkAt, lifecycle, startedAt, uiStreaming]);
}
