import { create } from "zustand";
import {
  isMessageStreamActiveState,
  isMessageStreamTerminalState,
  type MessageStreamLifecycleState
} from "@/features/chat";

export interface MessageStreamingState {
  lifecycle: MessageStreamLifecycleState;
  activeMessageId: string | null;
  streamStartedAt: string | null;
  streamCompletedAt: string | null;
  lastChunkAt: string | null;
  errorMessage: string | null;
}

export interface MessageStreamingActions {
  startStream: (messageId: string) => void;
  markStreaming: (messageId: string) => void;
  markPaused: (messageId: string) => void;
  markCompleted: (messageId: string) => void;
  markInterrupted: (messageId: string, reason?: string) => void;
  markFailed: (messageId: string | null, errorMessage: string) => void;
  markIdle: () => void;
}

export type MessageStreamingStore = MessageStreamingState & MessageStreamingActions;

export const initialMessageStreamingState: MessageStreamingState = {
  lifecycle: "idle",
  activeMessageId: null,
  streamStartedAt: null,
  streamCompletedAt: null,
  lastChunkAt: null,
  errorMessage: null
};

function nowIso() {
  return new Date().toISOString();
}

export const useMessageStreamingStore = create<MessageStreamingStore>((set) => ({
  ...initialMessageStreamingState,
  startStream: (messageId) => {
    if (!messageId) return;

    set({
      lifecycle: "starting",
      activeMessageId: messageId,
      streamStartedAt: nowIso(),
      streamCompletedAt: null,
      lastChunkAt: null,
      errorMessage: null
    });
  },
  markStreaming: (messageId) => {
    if (!messageId) return;

    set((state) => {
      const shouldKeepStartTime = state.activeMessageId === messageId && state.streamStartedAt !== null;
      return {
        lifecycle: "streaming",
        activeMessageId: messageId,
        streamStartedAt: shouldKeepStartTime ? state.streamStartedAt : nowIso(),
        streamCompletedAt: null,
        lastChunkAt: nowIso(),
        errorMessage: null
      };
    });
  },
  markPaused: (messageId) => {
    if (!messageId) return;

    set((state) => {
      const canPauseActive = state.activeMessageId === messageId && isMessageStreamActiveState(state.lifecycle);
      if (!canPauseActive) {
        return state;
      }

      return {
        lifecycle: "paused",
        lastChunkAt: nowIso()
      };
    });
  },
  markCompleted: (messageId) => {
    if (!messageId) return;

    set((state) => {
      if (state.activeMessageId !== messageId) {
        return state;
      }

      return {
        lifecycle: "completed",
        streamCompletedAt: nowIso(),
        lastChunkAt: nowIso(),
        errorMessage: null
      };
    });
  },
  markInterrupted: (messageId, reason) => {
    if (!messageId) return;

    set((state) => {
      if (state.activeMessageId !== messageId || isMessageStreamTerminalState(state.lifecycle)) {
        return state;
      }

      return {
        lifecycle: "interrupted",
        streamCompletedAt: nowIso(),
        lastChunkAt: nowIso(),
        errorMessage: reason ?? null
      };
    });
  },
  markFailed: (messageId, errorMessage) => {
    set((state) => {
      const activeMessageId = messageId ?? state.activeMessageId;

      return {
        lifecycle: "failed",
        activeMessageId,
        streamCompletedAt: nowIso(),
        lastChunkAt: nowIso(),
        errorMessage
      };
    });
  },
  markIdle: () => {
    set(initialMessageStreamingState);
  }
}));
