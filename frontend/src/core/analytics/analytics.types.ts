import type { FunnelStage, PersonaType } from "@/types";

export const ANALYTICS_EVENT_NAMES = [
  "chat_workspace_opened",
  "new_chat_clicked",
  "conversation_selected",
  "message_composer_focused",
  "message_sent",
  "assistant_response_started",
  "assistant_response_completed",
  "assistant_response_failed",
  "message_copied",
  "message_regenerated",
  "user_message_edited",
  "suggested_prompt_clicked",
  "label_applied",
  "label_removed",
  "conversation_renamed",
  "conversation_deleted",
  "conversation_archived",
  "conversation_pinned",
  "cta_clicked",
  "info_expanded",
  "persona_detected",
  "stage_changed",
  "session_end"
] as const;

export type AnalyticsEventName = (typeof ANALYTICS_EVENT_NAMES)[number];

export interface AnalyticsContext {
  sessionId?: string | null;
  ts?: string;
  source?: string;
}

export interface MessageSentPayload {
  channel: "input" | "suggested_action";
  messageLength: number;
  hasSession: boolean;
  conversationId?: string | null;
}

export interface CtaClickedPayload {
  ctaId: string;
  ctaKind?: string;
  position?: number;
}

export interface InfoExpandedPayload {
  sectionId: string;
  expanded: boolean;
  source: "message_section" | "intelligence";
}

export interface PersonaDetectedPayload {
  persona: PersonaType;
  confidence?: number | null;
}

export interface StageChangedPayload {
  fromStage?: FunnelStage | null;
  toStage: FunnelStage;
}

export interface SessionEndPayload {
  reason: "manual" | "timeout" | "unload" | "navigation";
  messageCount: number;
  durationMs?: number;
}

export interface ChatWorkspaceOpenedPayload {
  conversationId?: string | null;
  hasActiveConversation: boolean;
}

export interface NewChatClickedPayload {
  conversationId?: string | null;
  view: "all_chats" | "project" | "archived";
}

export interface ConversationSelectedPayload {
  conversationId: string;
  position?: number;
  source: "sidebar";
}

export interface MessageComposerFocusedPayload {
  conversationId?: string | null;
}

export interface AssistantResponseStartedPayload {
  conversationId?: string | null;
  requestId: string;
}

export interface AssistantResponseCompletedPayload {
  conversationId?: string | null;
  requestId: string;
  durationMs: number;
}

export interface AssistantResponseFailedPayload {
  conversationId?: string | null;
  requestId?: string;
  durationMs?: number;
  errorCode?: string;
}

export interface MessageCopiedPayload {
  conversationId?: string | null;
  messageId?: string;
  role?: "user" | "agent" | "system";
}

export interface MessageRegeneratedPayload {
  conversationId?: string | null;
  sourceMessageId?: string;
}

export interface UserMessageEditedPayload {
  conversationId?: string | null;
  messageId?: string;
}

export interface SuggestedPromptClickedPayload {
  conversationId?: string | null;
  promptId: string;
}

export interface LabelAppliedPayload {
  conversationId?: string | null;
  labelId: string;
}

export interface LabelRemovedPayload {
  conversationId?: string | null;
  labelId: string;
}

export interface ConversationRenamedPayload {
  conversationId: string;
}

export interface ConversationDeletedPayload {
  conversationId: string;
}

export interface ConversationArchivedPayload {
  conversationId: string;
  archived: boolean;
}

export interface ConversationPinnedPayload {
  conversationId: string;
  pinned: boolean;
}

export interface AnalyticsEventPayloadMap {
  chat_workspace_opened: ChatWorkspaceOpenedPayload;
  new_chat_clicked: NewChatClickedPayload;
  conversation_selected: ConversationSelectedPayload;
  message_composer_focused: MessageComposerFocusedPayload;
  message_sent: MessageSentPayload;
  assistant_response_started: AssistantResponseStartedPayload;
  assistant_response_completed: AssistantResponseCompletedPayload;
  assistant_response_failed: AssistantResponseFailedPayload;
  message_copied: MessageCopiedPayload;
  message_regenerated: MessageRegeneratedPayload;
  user_message_edited: UserMessageEditedPayload;
  suggested_prompt_clicked: SuggestedPromptClickedPayload;
  label_applied: LabelAppliedPayload;
  label_removed: LabelRemovedPayload;
  conversation_renamed: ConversationRenamedPayload;
  conversation_deleted: ConversationDeletedPayload;
  conversation_archived: ConversationArchivedPayload;
  conversation_pinned: ConversationPinnedPayload;
  cta_clicked: CtaClickedPayload;
  info_expanded: InfoExpandedPayload;
  persona_detected: PersonaDetectedPayload;
  stage_changed: StageChangedPayload;
  session_end: SessionEndPayload;
}

export interface AnalyticsEvent<TEventName extends AnalyticsEventName = AnalyticsEventName> {
  id: string;
  name: TEventName;
  payload: AnalyticsEventPayloadMap[TEventName];
  ts: string;
  sessionId?: string | null;
  source?: string;
}
