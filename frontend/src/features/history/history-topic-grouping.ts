import type { ConversationMetadata } from "@/types";
import type { HistoryConversationRecord } from "@/services/history";
import type { ConversationHistoryItem, ConversationTopicGroup } from "./history-topics.types";

interface TopicDescriptor {
  topicId: string;
  topicLabel: string;
  topicSlug?: string;
  summary?: string;
}

function readNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function toSlug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\u0600-\u06FF]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const GENERIC_TITLE_PATTERNS = [
  "new chat",
  "untitled conversation",
  "new conversation",
  "محادثة جديدة",
  "محادثة بدون عنوان",
  "گفتگوی جدید",
  "گفتگوی بدون عنوان",
  "چت جدید"
];

const GENERIC_TOPIC_TOKENS = new Set([
  "a",
  "an",
  "and",
  "assistant",
  "chat",
  "conversation",
  "continue",
  "for",
  "from",
  "how",
  "in",
  "is",
  "it",
  "my",
  "new",
  "of",
  "on",
  "or",
  "please",
  "resume",
  "start",
  "the",
  "to",
  "with",
  "موضوع",
  "گفتگو",
  "چت",
  "محادثة",
  "دردشة",
  "على",
  "حول",
  "من",
  "برای"
]);

const TOKEN_SYNONYMS: Record<string, string> = {
  analyse: "analyze",
  analyzing: "analyze",
  analysis: "analyze",
  reviewing: "review",
  reviewed: "review",
  earnings: "earning",
  opportunities: "opportunity",
  wallets: "wallet",
  risks: "risk",
  investments: "investment",
  strategies: "strategy",
  tokens: "token",
  defi: "defi",
  portfolio: "portfolio"
};

function isGenericTitle(title: string): boolean {
  const normalized = title.trim().toLowerCase();
  if (!normalized) return true;
  return GENERIC_TITLE_PATTERNS.some((pattern) => normalized === pattern);
}

function titleFromConversation(record: HistoryConversationRecord): string {
  const title = record.title.trim();
  const preview = record.preview.trim();

  if (title.length > 0 && !isGenericTitle(title)) return title;
  if (preview.length > 0) return preview;
  if (title.length > 0) return title;
  return record.id;
}

function tokenizeTopicSource(source: string): string[] {
  const matches = source.toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
  const normalized = matches
    .map((token) => TOKEN_SYNONYMS[token] ?? token)
    .filter((token) => token.length > 1 && !GENERIC_TOPIC_TOKENS.has(token));

  return [...new Set(normalized)];
}

function buildFallbackTopicId(source: string): string {
  const signatureTokens = tokenizeTopicSource(source).slice(0, 3).sort();
  if (signatureTokens.length === 0) {
    const sourceSlug = toSlug(source);
    return sourceSlug || "topic-misc";
  }
  return signatureTokens.join("-");
}

function deriveFallbackTopicLabel(record: HistoryConversationRecord): string {
  const source = titleFromConversation(record);
  const base = source.split(/[—\-:|]/)[0]?.trim() ?? "";
  if (base.length > 2) {
    return base.slice(0, 48);
  }
  return source.slice(0, 48);
}

function readMetadataTopic(record: HistoryConversationRecord): TopicDescriptor | null {
  const metadata = record.metadata as ConversationMetadata | undefined;
  if (!metadata) return null;

  const topicIdFromMetadata = readNonEmptyString(metadata.topicId);
  const topicLabelFromMetadata = readNonEmptyString(metadata.topicLabel);
  const topicSlugFromMetadata = readNonEmptyString(metadata.topicSlug);
  const topicSummaryFromMetadata = readNonEmptyString(metadata.topicSummary);
  const fallbackLabel = readNonEmptyString(metadata.topic);

  const topicLabel = topicLabelFromMetadata ?? fallbackLabel;
  if (!topicLabel) return null;

  const normalizedTopicId = topicIdFromMetadata ?? topicSlugFromMetadata ?? (toSlug(topicLabel) || `topic-${record.id}`);

  return {
    topicId: normalizedTopicId,
    topicLabel,
    topicSlug: topicSlugFromMetadata ?? toSlug(topicLabel),
    summary: topicSummaryFromMetadata ?? undefined
  };
}

function deriveTopic(record: HistoryConversationRecord): TopicDescriptor {
  const metadataTopic = readMetadataTopic(record);
  if (metadataTopic) return metadataTopic;

  const source = titleFromConversation(record);
  const topicLabel = deriveFallbackTopicLabel(record);
  const fallbackId = buildFallbackTopicId(source);
  const topicSlug = toSlug(topicLabel) || fallbackId;

  return {
    topicId: fallbackId || topicSlug || `topic-${record.id}`,
    topicLabel,
    topicSlug: topicSlug || undefined
  };
}

function toHistoryItem(record: HistoryConversationRecord, topicId: string): ConversationHistoryItem {
  return {
    ...record,
    conversationId: record.id,
    topicId
  };
}

function maxIsoTimestamp(timestamps: string[]): string {
  const sorted = [...timestamps].sort((left, right) => new Date(right).getTime() - new Date(left).getTime());
  return sorted[0] ?? new Date(0).toISOString();
}

export function groupConversationHistoryByTopic(records: HistoryConversationRecord[]): ConversationTopicGroup[] {
  const byTopic = new Map<string, ConversationTopicGroup>();

  records.forEach((record) => {
    const topic = deriveTopic(record);
    const existing = byTopic.get(topic.topicId);

    if (!existing) {
      byTopic.set(topic.topicId, {
        topicId: topic.topicId,
        topicLabel: topic.topicLabel,
        topicSlug: topic.topicSlug,
        summary: topic.summary,
        conversations: [toHistoryItem(record, topic.topicId)],
        updatedAt: record.updatedAt
      });
      return;
    }

    existing.conversations.push(toHistoryItem(record, topic.topicId));
    if (!existing.summary && topic.summary) {
      existing.summary = topic.summary;
    }
    existing.updatedAt = maxIsoTimestamp([existing.updatedAt, record.updatedAt]);
  });

  return Array.from(byTopic.values())
    .map((group) => ({
      ...group,
      conversations: [...group.conversations].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()),
      updatedAt: maxIsoTimestamp(group.conversations.map((item) => item.updatedAt))
    }))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}
