import type { AgentMessage, FunnelStage, MessageRole, PersonaType, SuggestedAction } from "@/types";
import { requestApi } from "./client";

export const CHAT_API_ENDPOINTS = {
  createSession: "/v1/session/start",
  sendMessage: "/v1/chat",
  getSessionSnapshot: (sessionId: string) => `/v1/session/${encodeURIComponent(sessionId)}`
} as const;

export interface CreateChatSessionPayload {
  userId: string;
  title?: string;
}

export interface SendChatMessagePayload {
  message: string;
  sessionId?: string;
  userId?: string;
  knowledgeLabels?: string[];
  memoryScope?: string;
  referralInviteCode?: string;
  attachments?: File[];
}

export interface ConversationMessageDto {
  id?: string;
  role?: string;
  text?: string;
  message?: string;
  created_at?: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export interface SuggestedActionDto {
  id?: string;
  label?: string;
  kind?: SuggestedAction["kind"];
  value?: string;
  disabled?: boolean;
  reason?: string;
  metadata?: Record<string, unknown>;
}

export interface ChatSessionSnapshotDto {
  session_id: string;
  persona?: string | null;
  confidence?: number | null;
  trust_score?: number | null;
  funnel_stage?: string;
  suggested_actions?: SuggestedActionDto[];
  conversation_messages?: ConversationMessageDto[];
  metadata?: Record<string, unknown>;
  state?: string;
}

export interface CreateChatSessionResponse {
  sessionId: string;
  persona?: PersonaType | string | null;
  confidence?: number | null;
  trustScore?: number | null;
  funnelStage?: FunnelStage | string;
  suggestedActions?: SuggestedAction[];
  conversationMessages?: AgentMessage[];
  metadata?: Record<string, unknown>;
  state?: string;
}

export interface SendChatMessageResponse {
  sessionId: string;
  message: string;
  role?: MessageRole | string;
  funnelStage?: FunnelStage | string;
  suggestedActions?: SuggestedAction[];
  timestamp?: string;
}

export interface SessionSnapshotResponse {
  sessionId: string;
  persona?: PersonaType | string | null;
  confidence?: number | null;
  trustScore?: number | null;
  funnelStage?: FunnelStage | string;
  suggestedActions?: SuggestedAction[];
  conversationMessages?: AgentMessage[];
  metadata?: Record<string, unknown>;
  state?: string;
}

interface CreateSessionResponseDto {
  session_id: string;
  state?: string;
}

interface SendMessageResponseDto {
  session_id: string;
  message: string;
  state?: string;
  actions?: string[];
  role?: string;
  timestamp?: string;
}

interface SendMessageRequestDto {
  session_id?: string;
  user_id?: string;
  message: string;
  knowledge_labels?: string[];
  memory_scope?: string;
  referral_invite_code?: string;
}

function toMessageRole(role: string | undefined): MessageRole {
  if (role === "user" || role === "system" || role === "agent") {
    return role;
  }

  if (role === "assistant") {
    return "agent";
  }

  return "system";
}

function toSuggestedAction(action: SuggestedActionDto, fallbackIndex: number): SuggestedAction {
  return {
    id: action.id ?? `suggested-action-${fallbackIndex}`,
    label: action.label ?? "Action",
    kind: action.kind ?? "primary",
    value: action.value,
    disabled: action.disabled,
    reason: action.reason,
    metadata: action.metadata
  };
}

function toAgentMessage(message: ConversationMessageDto, fallbackIndex: number): AgentMessage {
  const text = message.text ?? message.message ?? "";
  const createdAt = message.created_at ?? message.timestamp ?? new Date().toISOString();

  return {
    id: message.id ?? `message-${fallbackIndex}`,
    role: toMessageRole(message.role),
    text,
    createdAt,
    metadata: message.metadata
  };
}

function toSessionSnapshotResponse(dto: ChatSessionSnapshotDto): SessionSnapshotResponse {
  return {
    sessionId: dto.session_id,
    persona: dto.persona,
    confidence: dto.confidence,
    trustScore: dto.trust_score,
    funnelStage: dto.funnel_stage,
    suggestedActions: dto.suggested_actions?.map(toSuggestedAction),
    conversationMessages: dto.conversation_messages?.map(toAgentMessage),
    metadata: dto.metadata,
    state: dto.state
  };
}

function normalizeLabels(labels: string[] | undefined): string[] | undefined {
  if (!labels || labels.length === 0) {
    return undefined;
  }
  const normalized: string[] = [];
  const seen = new Set<string>();
  for (const raw of labels) {
    const label = raw.trim().toLowerCase();
    if (!label || seen.has(label)) {
      continue;
    }
    seen.add(label);
    normalized.push(label);
  }
  return normalized.length > 0 ? normalized : undefined;
}

export async function createChatSession(payload: CreateChatSessionPayload): Promise<CreateChatSessionResponse> {
  const body = {
    user_id: payload.userId,
    ...(payload.title ? { title: payload.title } : {})
  };

  const data = await requestApi<CreateSessionResponseDto, typeof body>({
    method: "POST",
    url: CHAT_API_ENDPOINTS.createSession,
    data: body
  });

  return {
    sessionId: data.session_id,
    state: data.state
  };
}

export async function sendChatMessage(payload: SendChatMessagePayload): Promise<SendChatMessageResponse> {
  const knowledgeLabels = normalizeLabels(payload.knowledgeLabels);
  const memoryScope = payload.memoryScope?.trim().toLowerCase() || undefined;
  const referralInviteCode = payload.referralInviteCode?.trim().toUpperCase() || undefined;
  const attachments = payload.attachments ?? [];

  let data: SendMessageResponseDto;
  if (attachments.length > 0) {
    const formData = new FormData();
    formData.set("message", payload.message);
    if (payload.sessionId) formData.set("session_id", payload.sessionId);
    if (payload.userId) formData.set("user_id", payload.userId);
    if (memoryScope) formData.set("memory_scope", memoryScope);
    if (referralInviteCode) formData.set("referral_invite_code", referralInviteCode);
    if (knowledgeLabels && knowledgeLabels.length > 0) {
      knowledgeLabels.forEach((label) => formData.append("knowledge_labels", label));
    }
    attachments.forEach((file) => formData.append("files", file));

    data = await requestApi<SendMessageResponseDto, FormData>({
      method: "POST",
      url: CHAT_API_ENDPOINTS.sendMessage,
      data: formData,
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  } else {
    const body: SendMessageRequestDto = {
      message: payload.message,
      ...(payload.sessionId ? { session_id: payload.sessionId } : {}),
      ...(payload.userId ? { user_id: payload.userId } : {}),
      ...(knowledgeLabels ? { knowledge_labels: knowledgeLabels } : {}),
      ...(memoryScope ? { memory_scope: memoryScope } : {}),
      ...(referralInviteCode ? { referral_invite_code: referralInviteCode } : {}),
    };

    data = await requestApi<SendMessageResponseDto, SendMessageRequestDto>({
      method: "POST",
      url: CHAT_API_ENDPOINTS.sendMessage,
      data: body,
    });
  }

  const suggestedActions = data.actions?.map((actionLabel, index) => ({
    id: `chat-action-${index}`,
    label: actionLabel,
    kind: "primary" as const
  }));

  return {
    sessionId: data.session_id,
    message: data.message,
    role: toMessageRole(data.role),
    funnelStage: data.state,
    suggestedActions,
    timestamp: data.timestamp
  };
}

export async function getSessionSnapshot(sessionId: string): Promise<SessionSnapshotResponse> {
  const data = await requestApi<ChatSessionSnapshotDto>({
    method: "GET",
    url: CHAT_API_ENDPOINTS.getSessionSnapshot(sessionId)
  });

  return toSessionSnapshotResponse(data);
}
