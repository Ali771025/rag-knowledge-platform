import type { FunnelStage, PersonaType, SuggestedAction } from "@/types";
import {
  normalizeAgentMessageContract,
  normalizeChatMessageRole,
  normalizeSuggestedActionsContract,
  normalizeTransportErrorContract,
  type ChatTransportErrorContract
} from "@/features/chat";

export const INCOMING_WS_EVENT_TYPES = [
  "message_stream",
  "message_complete",
  "suggested_actions",
  "persona_update",
  "stage_update",
  "session_update",
  "error",
  "connection_ack",
  "ready"
] as const;

export type IncomingWebSocketEventType = (typeof INCOMING_WS_EVENT_TYPES)[number];

export const OUTGOING_WS_EVENT_TYPES = ["user_message", "ping", "subscribe_session"] as const;
export type OutgoingWebSocketEventType = (typeof OUTGOING_WS_EVENT_TYPES)[number];

interface WebSocketEventEnvelope<TType extends string, TPayload> {
  type: TType;
  payload: TPayload;
  sessionId?: string;
  timestamp?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeText(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : fallback;
}

function normalizeNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export interface MessageStreamPayload {
  messageId: string;
  chunk: string;
  role?: "agent" | "user" | "system";
  isFinalChunk?: boolean;
  metadata?: Record<string, unknown>;
}

export interface MessageCompletePayload {
  message: ReturnType<typeof normalizeAgentMessageContract>;
}

export interface SuggestedActionsPayload {
  actions: SuggestedAction[];
}

export interface PersonaUpdatePayload {
  persona: PersonaType | string;
  confidence?: number | null;
}

export interface StageUpdatePayload {
  funnelStage: FunnelStage | string;
  trustScore?: number | null;
}

export interface SessionUpdatePayload {
  sessionId: string;
  persona?: PersonaType | string | null;
  confidence?: number | null;
  trustScore?: number | null;
  funnelStage?: FunnelStage | string;
  suggestedActions?: SuggestedAction[];
  metadata?: Record<string, unknown>;
}

export type ErrorEventPayload = ChatTransportErrorContract;

export interface ConnectionAckPayload {
  sessionId?: string;
  ready?: boolean;
  serverTime?: string;
}

export type MessageStreamEvent = WebSocketEventEnvelope<"message_stream", MessageStreamPayload>;
export type MessageCompleteEvent = WebSocketEventEnvelope<"message_complete", MessageCompletePayload>;
export type SuggestedActionsEvent = WebSocketEventEnvelope<"suggested_actions", SuggestedActionsPayload>;
export type PersonaUpdateEvent = WebSocketEventEnvelope<"persona_update", PersonaUpdatePayload>;
export type StageUpdateEvent = WebSocketEventEnvelope<"stage_update", StageUpdatePayload>;
export type SessionUpdateEvent = WebSocketEventEnvelope<"session_update", SessionUpdatePayload>;
export type ErrorEvent = WebSocketEventEnvelope<"error", ErrorEventPayload>;
export type ConnectionAckEvent = WebSocketEventEnvelope<"connection_ack" | "ready", ConnectionAckPayload>;

export type IncomingWebSocketEvent =
  | MessageStreamEvent
  | MessageCompleteEvent
  | SuggestedActionsEvent
  | PersonaUpdateEvent
  | StageUpdateEvent
  | SessionUpdateEvent
  | ErrorEvent
  | ConnectionAckEvent;

export interface UserMessagePayload {
  message: string;
  sessionId?: string;
  userId?: string;
  metadata?: Record<string, unknown>;
}

export interface PingPayload {
  sentAt?: string;
}

export interface SubscribeSessionPayload {
  sessionId: string;
}

export type UserMessageEvent = WebSocketEventEnvelope<"user_message", UserMessagePayload>;
export type PingEvent = WebSocketEventEnvelope<"ping", PingPayload>;
export type SubscribeSessionEvent = WebSocketEventEnvelope<"subscribe_session", SubscribeSessionPayload>;

export type OutgoingWebSocketEvent = UserMessageEvent | PingEvent | SubscribeSessionEvent;

export function isIncomingWebSocketEventType(value: unknown): value is IncomingWebSocketEventType {
  return typeof value === "string" && INCOMING_WS_EVENT_TYPES.includes(value as IncomingWebSocketEventType);
}

export function isOutgoingWebSocketEventType(value: unknown): value is OutgoingWebSocketEventType {
  return typeof value === "string" && OUTGOING_WS_EVENT_TYPES.includes(value as OutgoingWebSocketEventType);
}

function hasEnvelopeShape(value: unknown): value is Record<string, unknown> {
  return isRecord(value) && "type" in value && "payload" in value;
}

export function normalizeIncomingWebSocketEvent(value: unknown): IncomingWebSocketEvent | null {
  if (!hasEnvelopeShape(value) || !isIncomingWebSocketEventType(value.type)) {
    return null;
  }

  const timestamp = typeof value.timestamp === "string" ? value.timestamp : undefined;
  const sessionId = typeof value.sessionId === "string" ? value.sessionId : undefined;

  if (!isRecord(value.payload)) {
    return null;
  }

  switch (value.type) {
    case "message_stream": {
      const messageId = normalizeText(value.payload.messageId);
      const chunk = typeof value.payload.chunk === "string" ? value.payload.chunk : "";
      if (!messageId) {
        return null;
      }

      return {
        type: "message_stream",
        timestamp,
        sessionId,
        payload: {
          messageId,
          chunk,
          role: normalizeChatMessageRole(value.payload.role, "agent"),
          isFinalChunk: typeof value.payload.isFinalChunk === "boolean" ? value.payload.isFinalChunk : undefined,
          metadata: isRecord(value.payload.metadata) ? { ...value.payload.metadata } : undefined
        }
      };
    }

    case "message_complete": {
      return {
        type: "message_complete",
        timestamp,
        sessionId,
        payload: {
          message: normalizeAgentMessageContract(value.payload.message)
        }
      };
    }

    case "suggested_actions": {
      return {
        type: "suggested_actions",
        timestamp,
        sessionId,
        payload: {
          actions: normalizeSuggestedActionsContract(value.payload.actions)
        }
      };
    }

    case "persona_update": {
      const persona = normalizeText(value.payload.persona);
      if (!persona) {
        return null;
      }

      return {
        type: "persona_update",
        timestamp,
        sessionId,
        payload: {
          persona,
          confidence: normalizeNumber(value.payload.confidence)
        }
      };
    }

    case "stage_update": {
      const funnelStage = normalizeText(value.payload.funnelStage);
      if (!funnelStage) {
        return null;
      }

      return {
        type: "stage_update",
        timestamp,
        sessionId,
        payload: {
          funnelStage,
          trustScore: normalizeNumber(value.payload.trustScore)
        }
      };
    }

    case "session_update": {
      const sessionIdValue = normalizeText(value.payload.sessionId);
      if (!sessionIdValue) {
        return null;
      }

      return {
        type: "session_update",
        timestamp,
        sessionId,
        payload: {
          sessionId: sessionIdValue,
          persona: typeof value.payload.persona === "string" || value.payload.persona === null ? value.payload.persona : undefined,
          confidence: normalizeNumber(value.payload.confidence),
          trustScore: normalizeNumber(value.payload.trustScore),
          funnelStage: typeof value.payload.funnelStage === "string" ? value.payload.funnelStage : undefined,
          suggestedActions: normalizeSuggestedActionsContract(value.payload.suggestedActions),
          metadata: isRecord(value.payload.metadata) ? { ...value.payload.metadata } : undefined
        }
      };
    }

    case "error": {
      return {
        type: "error",
        timestamp,
        sessionId,
        payload: normalizeTransportErrorContract(value.payload)
      };
    }

    case "connection_ack":
    case "ready": {
      return {
        type: value.type,
        timestamp,
        sessionId,
        payload: {
          sessionId: typeof value.payload.sessionId === "string" ? value.payload.sessionId : undefined,
          ready: typeof value.payload.ready === "boolean" ? value.payload.ready : undefined,
          serverTime: typeof value.payload.serverTime === "string" ? value.payload.serverTime : undefined
        }
      };
    }

    default:
      return null;
  }
}

export function isIncomingWebSocketEvent(value: unknown): value is IncomingWebSocketEvent {
  return normalizeIncomingWebSocketEvent(value) !== null;
}

export function isOutgoingWebSocketEvent(value: unknown): value is OutgoingWebSocketEvent {
  if (!hasEnvelopeShape(value) || !isOutgoingWebSocketEventType(value.type)) {
    return false;
  }

  if (!isRecord(value.payload)) {
    return false;
  }

  if (value.type === "user_message") {
    return typeof value.payload.message === "string" && value.payload.message.trim().length > 0;
  }

  if (value.type === "ping") {
    return value.payload.sentAt === undefined || typeof value.payload.sentAt === "string";
  }

  if (value.type === "subscribe_session") {
    return typeof value.payload.sessionId === "string" && value.payload.sessionId.trim().length > 0;
  }

  return false;
}
