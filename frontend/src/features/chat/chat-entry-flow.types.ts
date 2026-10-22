export type ChatEntryMode = "history-choice" | "continue" | "new";
export type ChatEntrySource = "history";

export interface HistoryChatEntryNavigationState {
  source: ChatEntrySource;
  chatEntryMode: "history-choice";
  selectedTopicId: string;
  selectedTopicLabel: string;
  selectedConversationId: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function parseHistoryChatEntryNavigationState(value: unknown): HistoryChatEntryNavigationState | null {
  if (!isRecord(value)) return null;

  const source = readNonEmptyString(value.source);
  const chatEntryMode = readNonEmptyString(value.chatEntryMode);
  const selectedTopicId = readNonEmptyString(value.selectedTopicId);
  const selectedTopicLabel = readNonEmptyString(value.selectedTopicLabel);
  const selectedConversationIdRaw = value.selectedConversationId;

  if (source !== "history") return null;
  if (chatEntryMode !== "history-choice") return null;
  if (!selectedTopicId || !selectedTopicLabel) return null;

  if (selectedConversationIdRaw !== null && typeof selectedConversationIdRaw !== "string") {
    return null;
  }

  return {
    source,
    chatEntryMode,
    selectedTopicId,
    selectedTopicLabel,
    selectedConversationId: readNonEmptyString(selectedConversationIdRaw) ?? null
  };
}
