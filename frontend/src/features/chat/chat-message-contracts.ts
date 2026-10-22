import {
  MESSAGE_ROLES,
  type AgentMessage,
  type ExpandableSection,
  type MessageCard,
  type MessageRole,
  type SuggestedAction
} from "@/types";

export const CHAT_MESSAGE_KINDS = ["user", "assistant", "system", "status", "error"] as const;
export type ChatMessageKind = (typeof CHAT_MESSAGE_KINDS)[number];

export interface ChatMessageContractBase {
  id: string;
  kind: ChatMessageKind;
  role: MessageRole;
  text: string;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export interface ChatUserMessageContract extends ChatMessageContractBase {
  kind: "user";
  role: "user";
}

export interface ChatAssistantMessageContract extends ChatMessageContractBase {
  kind: "assistant";
  role: "agent";
}

export interface ChatSystemMessageContract extends ChatMessageContractBase {
  kind: "system";
  role: "system";
}

export interface ChatStatusMessageContract extends ChatMessageContractBase {
  kind: "status";
}

export interface ChatErrorMessageContract extends ChatMessageContractBase {
  kind: "error";
}

export type ChatMessageContract =
  | ChatUserMessageContract
  | ChatAssistantMessageContract
  | ChatSystemMessageContract
  | ChatStatusMessageContract
  | ChatErrorMessageContract;

export interface ChatTransportErrorContract {
  code: string;
  message: string;
  recoverable: boolean;
  details: Record<string, unknown>;
}

interface NormalizeAgentMessageFallback {
  id?: string;
  role?: MessageRole;
  text?: string;
  createdAt?: string;
  isStreaming?: boolean;
  metadata?: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeText(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : fallback;
}

function normalizeOptionalText(value: unknown): string | undefined {
  const normalized = normalizeText(value);
  return normalized.length > 0 ? normalized : undefined;
}

function normalizeMetadata(value: unknown): Record<string, unknown> {
  return isRecord(value) ? { ...value } : {};
}

function normalizeCreatedAt(value: unknown): string {
  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  return new Date().toISOString();
}

function normalizeSuggestedAction(value: unknown, index: number): SuggestedAction | null {
  if (!isRecord(value)) return null;

  const kindValue = normalizeText(value.kind, "secondary");
  const kind: SuggestedAction["kind"] =
    kindValue === "primary" || kindValue === "secondary" || kindValue === "link" || kindValue === "system"
      ? kindValue
      : "secondary";
  const id = normalizeText(value.id, `suggested-action-${index + 1}`);
  const label = normalizeText(value.label);

  if (!label) {
    return null;
  }

  return {
    id,
    label,
    kind,
    value: normalizeOptionalText(value.value),
    disabled: typeof value.disabled === "boolean" ? value.disabled : undefined,
    reason: normalizeOptionalText(value.reason),
    metadata: isRecord(value.metadata) ? { ...value.metadata } : undefined
  };
}

function normalizeExpandableSection(value: unknown, index: number): ExpandableSection | null {
  if (!isRecord(value)) return null;

  const title = normalizeText(value.title);
  const content = normalizeText(value.content);
  if (!title || !content) {
    return null;
  }

  return {
    id: normalizeText(value.id, `section-${index + 1}`),
    title,
    content,
    initiallyExpanded: typeof value.initiallyExpanded === "boolean" ? value.initiallyExpanded : undefined
  };
}

function normalizeMessageCard(value: unknown, index: number): MessageCard | null {
  if (!isRecord(value)) return null;

  const title = normalizeText(value.title);
  if (!title) {
    return null;
  }

  return {
    id: normalizeText(value.id, `card-${index + 1}`),
    title,
    description: normalizeOptionalText(value.description),
    ctaLabel: normalizeOptionalText(value.ctaLabel),
    ctaValue: normalizeOptionalText(value.ctaValue),
    metadata: isRecord(value.metadata) ? { ...value.metadata } : undefined
  };
}

export function normalizeChatMessageRole(value: unknown, fallback: MessageRole = "agent"): MessageRole {
  if (typeof value !== "string") {
    return fallback;
  }

  return MESSAGE_ROLES.includes(value as MessageRole) ? (value as MessageRole) : fallback;
}

export function normalizeSuggestedActionsContract(value: unknown): SuggestedAction[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((action, index) => normalizeSuggestedAction(action, index))
    .filter((action): action is SuggestedAction => action !== null);
}

function normalizeExpandableSections(value: unknown): ExpandableSection[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((section, index) => normalizeExpandableSection(section, index))
    .filter((section): section is ExpandableSection => section !== null);
}

function normalizeMessageCards(value: unknown): MessageCard[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((card, index) => normalizeMessageCard(card, index)).filter((card): card is MessageCard => card !== null);
}

export function normalizeAgentMessageContract(
  value: unknown,
  fallback: NormalizeAgentMessageFallback = {}
): AgentMessage {
  const record = isRecord(value) ? value : {};
  const role = normalizeChatMessageRole(record.role, fallback.role ?? "agent");
  const id = normalizeText(record.id, fallback.id ?? `message-${Date.now()}`);
  const text = normalizeText(record.text, fallback.text ?? "");
  const createdAt = normalizeCreatedAt(record.createdAt ?? fallback.createdAt);
  const metadata = normalizeMetadata(record.metadata ?? fallback.metadata);
  const actions = normalizeSuggestedActionsContract(record.actions);
  const expandableSections = normalizeExpandableSections(record.expandableSections);
  const cards = normalizeMessageCards(record.cards);
  const isStreaming = typeof record.isStreaming === "boolean" ? record.isStreaming : fallback.isStreaming;

  return {
    id,
    role,
    text,
    createdAt,
    actions: actions.length > 0 ? actions : undefined,
    expandableSections: expandableSections.length > 0 ? expandableSections : undefined,
    cards: cards.length > 0 ? cards : undefined,
    metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
    isStreaming
  };
}

export function toChatMessageContract(message: AgentMessage): ChatMessageContract {
  const metadata = message.metadata ? { ...message.metadata } : {};
  const role = normalizeChatMessageRole(message.role, "agent");

  if (role === "user") {
    return {
      id: message.id,
      role: "user",
      kind: "user",
      text: message.text,
      createdAt: message.createdAt,
      metadata
    };
  }

  if (role === "system") {
    return {
      id: message.id,
      role: "system",
      kind: "system",
      text: message.text,
      createdAt: message.createdAt,
      metadata
    };
  }

  return {
    id: message.id,
    role: "agent",
    kind: "assistant",
    text: message.text,
    createdAt: message.createdAt,
    metadata
  };
}

export function isChatMessageContract(value: unknown): value is ChatMessageContract {
  if (!isRecord(value)) {
    return false;
  }

  const kind = value.kind;
  const role = value.role;

  if (typeof kind !== "string" || !CHAT_MESSAGE_KINDS.includes(kind as ChatMessageKind)) {
    return false;
  }

  if (!MESSAGE_ROLES.includes(role as MessageRole)) {
    return false;
  }

  return (
    typeof value.id === "string" &&
    value.id.length > 0 &&
    typeof value.text === "string" &&
    typeof value.createdAt === "string" &&
    isRecord(value.metadata)
  );
}

export function normalizeTransportErrorContract(value: unknown): ChatTransportErrorContract {
  if (!isRecord(value)) {
    return {
      code: "UNKNOWN",
      message: "Unknown transport error",
      recoverable: true,
      details: {}
    };
  }

  return {
    code: normalizeText(value.code, "UNKNOWN"),
    message: normalizeText(value.message, "Unknown transport error"),
    recoverable: typeof value.recoverable === "boolean" ? value.recoverable : true,
    details: normalizeMetadata(value.details)
  };
}

export function isChatTransportErrorContract(value: unknown): value is ChatTransportErrorContract {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.code === "string" &&
    typeof value.message === "string" &&
    typeof value.recoverable === "boolean" &&
    isRecord(value.details)
  );
}
