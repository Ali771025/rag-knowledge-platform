import type { HistoryConversationRecord } from "@/services/history";

export type ConversationHistoryItem = HistoryConversationRecord & {
  conversationId: string;
  topicId: string;
};

export interface ConversationTopicGroup {
  topicId: string;
  topicLabel: string;
  topicSlug?: string;
  summary?: string;
  conversations: ConversationHistoryItem[];
  updatedAt: string;
}
