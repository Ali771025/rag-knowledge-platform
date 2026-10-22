import { workspaceConversationRepository } from "@/core/workspace/repositories";
import type { Conversation, ConversationMetadata, ConversationStatus } from "@/types";

export interface HistoryConversationRecord {
  id: string;
  title: string;
  updatedAt: string;
  status: ConversationStatus;
  preview: string;
  language: string | null;
  metadata?: ConversationMetadata;
}

export interface HistoryService {
  listConversationHistory: () => Promise<HistoryConversationRecord[]>;
}

function readLanguage(metadata: ConversationMetadata | undefined): string | null {
  if (!metadata) return null;
  const value = metadata.language;
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function toPreview(conversation: Conversation): string {
  const lastMessage = conversation.messages[conversation.messages.length - 1];
  if (!lastMessage) return "";
  return lastMessage.text.trim();
}

class LocalHistoryService implements HistoryService {
  async listConversationHistory(): Promise<HistoryConversationRecord[]> {
    const conversations = workspaceConversationRepository
      .listConversations()
      .filter((conversation) => conversation.status !== "deleted")
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());

    return conversations.map((conversation) => ({
      id: conversation.id,
      title: conversation.title,
      updatedAt: conversation.updatedAt,
      status: conversation.status,
      preview: toPreview(conversation),
      language: readLanguage(conversation.metadata),
      metadata: conversation.metadata
    }));
  }
}

export const historyService: HistoryService = new LocalHistoryService();
