import type { FunnelStage, PersonaType } from "@/types";
import { analyticsTracker } from "@/core/analytics";
import { useSessionStore } from "@/state";

export function useAnalytics() {
  const sessionId = useSessionStore((state) => state.sessionId);

  const trackEvent = <TEventName extends Parameters<typeof analyticsTracker.track>[0]>(
    name: TEventName,
    payload: Parameters<typeof analyticsTracker.track<TEventName>>[1]
  ) => {
    analyticsTracker.track(name, payload, {
      sessionId,
      source: "ui"
    });
  };

  const trackWorkspaceOpened = (conversationId: string | null, hasActiveConversation: boolean) => {
    trackEvent("chat_workspace_opened", { conversationId, hasActiveConversation });
  };

  const trackNewChatClicked = (view: "all_chats" | "project" | "archived", conversationId?: string | null) => {
    trackEvent("new_chat_clicked", { view, conversationId });
  };

  const trackConversationSelected = (conversationId: string, position?: number) => {
    trackEvent("conversation_selected", { conversationId, position, source: "sidebar" });
  };

  const trackMessageComposerFocused = (conversationId?: string | null) => {
    trackEvent("message_composer_focused", { conversationId });
  };

  const trackMessageSent = (messageLength: number, channel: "input" | "suggested_action", conversationId?: string | null) => {
    trackEvent("message_sent", {
      messageLength,
      channel,
      hasSession: Boolean(sessionId),
      conversationId
    });
  };

  const trackAssistantResponseStarted = (requestId: string, conversationId?: string | null) => {
    trackEvent("assistant_response_started", { requestId, conversationId });
  };

  const trackAssistantResponseCompleted = (requestId: string, durationMs: number, conversationId?: string | null) => {
    trackEvent("assistant_response_completed", { requestId, durationMs, conversationId });
  };

  const trackAssistantResponseFailed = (params: {
    requestId?: string;
    durationMs?: number;
    errorCode?: string;
    conversationId?: string | null;
  }) => {
    trackEvent("assistant_response_failed", params);
  };

  const trackMessageCopied = (messageId?: string, role?: "user" | "agent" | "system", conversationId?: string | null) => {
    trackEvent("message_copied", { messageId, role, conversationId });
  };

  const trackMessageRegenerated = (sourceMessageId?: string, conversationId?: string | null) => {
    trackEvent("message_regenerated", { sourceMessageId, conversationId });
  };

  const trackUserMessageEdited = (messageId?: string, conversationId?: string | null) => {
    trackEvent("user_message_edited", { messageId, conversationId });
  };

  const trackSuggestedPromptClicked = (promptId: string, conversationId?: string | null) => {
    trackEvent("suggested_prompt_clicked", { promptId, conversationId });
  };

  const trackLabelApplied = (labelId: string, conversationId?: string | null) => {
    trackEvent("label_applied", { labelId, conversationId });
  };

  const trackLabelRemoved = (labelId: string, conversationId?: string | null) => {
    trackEvent("label_removed", { labelId, conversationId });
  };

  const trackConversationRenamed = (conversationId: string) => {
    trackEvent("conversation_renamed", { conversationId });
  };

  const trackConversationDeleted = (conversationId: string) => {
    trackEvent("conversation_deleted", { conversationId });
  };

  const trackConversationArchived = (conversationId: string, archived: boolean) => {
    trackEvent("conversation_archived", { conversationId, archived });
  };

  const trackConversationPinned = (conversationId: string, pinned: boolean) => {
    trackEvent("conversation_pinned", { conversationId, pinned });
  };

  const trackCtaClicked = (ctaId: string, ctaKind?: string, position?: number) => {
    trackEvent("cta_clicked", { ctaId, ctaKind, position });
  };

  const trackInfoExpanded = (sectionId: string, expanded: boolean, source: "message_section" | "intelligence") => {
    trackEvent("info_expanded", { sectionId, expanded, source });
  };

  const trackPersonaDetected = (persona: PersonaType, confidence?: number | null) => {
    trackEvent("persona_detected", { persona, confidence });
  };

  const trackStageChanged = (toStage: FunnelStage, fromStage?: FunnelStage | null) => {
    trackEvent("stage_changed", { toStage, fromStage });
  };

  const trackSessionEnd = (reason: "manual" | "timeout" | "unload" | "navigation", messageCount: number) => {
    trackEvent("session_end", { reason, messageCount });
  };

  return {
    trackEvent,
    trackWorkspaceOpened,
    trackNewChatClicked,
    trackConversationSelected,
    trackMessageComposerFocused,
    trackMessageSent,
    trackAssistantResponseStarted,
    trackAssistantResponseCompleted,
    trackAssistantResponseFailed,
    trackMessageCopied,
    trackMessageRegenerated,
    trackUserMessageEdited,
    trackSuggestedPromptClicked,
    trackLabelApplied,
    trackLabelRemoved,
    trackConversationRenamed,
    trackConversationDeleted,
    trackConversationArchived,
    trackConversationPinned,
    trackCtaClicked,
    trackInfoExpanded,
    trackPersonaDetected,
    trackStageChanged,
    trackSessionEnd
  };
}
