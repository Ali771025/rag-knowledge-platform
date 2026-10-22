import {
  FUNNEL_STAGES,
  PERSONA_TYPES,
  type FunnelStage,
  type PersonaType,
  type SessionStateSnapshot
} from "@/types";
import { normalizeAgentMessageContract } from "@/features/chat";
import { useChatStore, useMessageStreamingStore, useSessionStore, useUiStore } from "@/state";
import type { IncomingWebSocketEvent } from "./websocket-events";

function normalizePersona(value: string | null | undefined): PersonaType {
  if (!value) return "UNKNOWN";
  return PERSONA_TYPES.includes(value as PersonaType) ? (value as PersonaType) : "UNKNOWN";
}

function normalizeFunnelStage(value: string | undefined): FunnelStage | null {
  if (!value) return null;
  return FUNNEL_STAGES.includes(value as FunnelStage) ? (value as FunnelStage) : null;
}

export function handleWebSocketEvent(event: IncomingWebSocketEvent): void {
  const chatStore = useChatStore.getState();
  const messageStreamingStore = useMessageStreamingStore.getState();
  const sessionStore = useSessionStore.getState();
  const uiStore = useUiStore.getState();

  switch (event.type) {
    case "message_stream": {
      const { messageId, chunk, role, metadata, isFinalChunk } = event.payload;
      if (!messageId) {
        return;
      }

      // Assumption: backend emits a stable messageId for each active agent stream.
      messageStreamingStore.startStream(messageId);
      chatStore.startStreamingMessage(messageId, {
        role: role ?? "agent",
        metadata,
        createdAt: event.timestamp
      });
      messageStreamingStore.markStreaming(messageId);

      if (chunk) {
        chatStore.appendToStreamingMessage(messageId, chunk);
      }

      uiStore.setStreaming(true);
      uiStore.setTyping(true);

      if (isFinalChunk) {
        chatStore.completeStreamingMessage(messageId);
        messageStreamingStore.markCompleted(messageId);
        uiStore.setStreaming(false);
        uiStore.setTyping(false);
      }

      return;
    }

    case "message_complete": {
      const completedMessage = normalizeAgentMessageContract(event.payload.message, { isStreaming: false });

      chatStore.completeStreamingMessage(completedMessage.id, completedMessage);
      messageStreamingStore.markCompleted(completedMessage.id);

      uiStore.setStreaming(false);
      uiStore.setTyping(false);
      return;
    }

    case "suggested_actions": {
      sessionStore.setSuggestedActions(event.payload.actions);
      return;
    }

    case "persona_update": {
      sessionStore.updatePersona(normalizePersona(event.payload.persona), event.payload.confidence ?? null);
      return;
    }

    case "stage_update": {
      const normalizedStage = normalizeFunnelStage(event.payload.funnelStage);
      if (normalizedStage) {
        sessionStore.updateStage(normalizedStage);
      }

      if (event.payload.trustScore !== undefined) {
        sessionStore.updateTrustScore(event.payload.trustScore ?? null);
      }
      return;
    }

    case "session_update": {
      const normalizedStage = normalizeFunnelStage(event.payload.funnelStage);
      const partial: Partial<SessionStateSnapshot> = { sessionId: event.payload.sessionId };

      if (event.payload.persona !== undefined) {
        partial.persona = normalizePersona(event.payload.persona);
      }

      if (event.payload.confidence !== undefined) {
        partial.confidence = event.payload.confidence;
      }

      if (event.payload.trustScore !== undefined) {
        partial.trustScore = event.payload.trustScore;
      }

      if (event.payload.suggestedActions !== undefined) {
        partial.suggestedActions = event.payload.suggestedActions;
      }

      if (event.payload.metadata !== undefined) {
        partial.metadata = event.payload.metadata;
      }

      if (normalizedStage) {
        partial.funnelStage = normalizedStage;
      }

      sessionStore.patchSession(partial);
      return;
    }

    case "error": {
      uiStore.setError({
        message: event.payload.message || "Real-time channel returned an error.",
        code: event.payload.code,
        source: "network"
      });
      messageStreamingStore.markFailed(messageStreamingStore.activeMessageId, event.payload.message);
      uiStore.setStreaming(false);
      uiStore.setTyping(false);
      return;
    }

    case "connection_ack":
    case "ready": {
      if (event.payload.sessionId) {
        sessionStore.patchSession({ sessionId: event.payload.sessionId });
      }
      uiStore.clearError();
      return;
    }

    default: {
      const exhaustiveCheck: never = event;
      return exhaustiveCheck;
    }
  }
}
