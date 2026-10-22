import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronRight, History, MessageSquareText, Search, Tag } from "lucide-react";
import { appRoutes } from "@/app/routes/contracts";
import {
  Button,
  CardShell,
  EmptyState,
  ErrorPanel,
  InputShell,
  LoadingSkeleton,
  MotionList,
  MotionListItem,
  MotionPage,
  PageContainer,
  ScreenShell,
  SectionContainer
} from "@/components/ui";
import { dsTypography } from "@/design-system";
import { useI18n } from "@/i18n";
import { historyService } from "@/services/history";
import { useChatEntryFlowStore } from "@/state";
import type { HistoryChatEntryNavigationState } from "@/features/chat/chat-entry-flow.types";
import { groupConversationHistoryByTopic } from "./history-topic-grouping";
import type { ConversationHistoryItem, ConversationTopicGroup } from "./history-topics.types";

type HistoryLoadStatus = "loading" | "success" | "error";

function toPreviewText(preview: string, fallback: string): string {
  const trimmed = preview.trim();
  if (!trimmed) return fallback;
  if (trimmed.length <= 140) return trimmed;
  return `${trimmed.slice(0, 137)}...`;
}

function formatTimestamp(value: string, locale: string): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function normalizeSearchValue(value: string): string {
  return value.trim().toLowerCase();
}

function topicGroupMatchesQuery(group: ConversationTopicGroup, normalizedQuery: string): boolean {
  if (!normalizedQuery) return true;

  const topicMatch = group.topicLabel.toLowerCase().includes(normalizedQuery);
  const summaryMatch = group.summary?.toLowerCase().includes(normalizedQuery) ?? false;
  const conversationMatch = group.conversations.some((conversation) => {
    return conversation.title.toLowerCase().includes(normalizedQuery) || conversation.preview.toLowerCase().includes(normalizedQuery);
  });
  return topicMatch || summaryMatch || conversationMatch;
}

function formatConversationCount(total: number, label: string): string {
  return `${total} ${label}`;
}

function HistorySearch({
  query,
  onChange,
  onClear,
  placeholder,
  ariaLabel,
  clearLabel
}: {
  query: string;
  onChange: (next: string) => void;
  onClear: () => void;
  placeholder: string;
  ariaLabel: string;
  clearLabel: string;
}) {
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <InputShell
        type="search"
        value={query}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className="pe-20 ps-9"
      />
      {query.trim().length > 0 ? (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md border border-border px-2 py-0.5 text-xs text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {clearLabel}
        </button>
      ) : null}
    </div>
  );
}

function TopicConversationRow({
  record,
  locale,
  onOpenConversation,
  labels
}: {
  record: ConversationHistoryItem;
  locale: string;
  onOpenConversation: (conversation: ConversationHistoryItem) => void;
  labels: {
    openConversationAria: string;
    statusActive: string;
    statusArchived: string;
    untitledConversation: string;
    noPreview: string;
  };
}) {
  const title = record.title.trim() || labels.untitledConversation;
  const preview = toPreviewText(record.preview, labels.noPreview);
  const statusLabel = record.status === "archived" ? labels.statusArchived : labels.statusActive;
  const timestamp = formatTimestamp(record.updatedAt, locale);

  return (
    <li className="rounded-xl border border-white/10 bg-white/5">
      <button
        type="button"
        onClick={() => onOpenConversation(record)}
        aria-label={`${labels.openConversationAria}: ${title}`}
        className="w-full rounded-xl p-3 text-left transition hover:bg-white/10"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-[color:var(--color-text-main)]">{title}</h3>
            <p className="mt-1 line-clamp-2 text-sm text-[color:var(--color-text-muted)]">{preview}</p>
          </div>
          <span className="shrink-0 rounded-full border border-white/15 bg-black/25 px-2 py-0.5 text-[11px] font-medium text-[color:var(--color-text-muted)]">
            {statusLabel}
          </span>
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
          {timestamp ? <span>{timestamp}</span> : null}
          {record.language ? <span className="rounded-full border border-white/15 px-1.5 py-0.5">{record.language}</span> : null}
        </div>
      </button>
    </li>
  );
}

function HistoryTopicGroupCard({
  topic,
  locale,
  onOpenTopic,
  onOpenConversation,
  labels,
  messages
}: {
  topic: ConversationTopicGroup;
  locale: string;
  onOpenTopic: (topic: ConversationTopicGroup) => void;
  onOpenConversation: (topic: ConversationTopicGroup, conversation: ConversationHistoryItem) => void;
  labels: {
    openConversationAria: string;
    statusActive: string;
    statusArchived: string;
    untitledConversation: string;
    noPreview: string;
  };
  messages: ReturnType<typeof useI18n>["messages"]["history"];
}) {
  const latestActivity = formatTimestamp(topic.updatedAt, locale);
  const recentConversations = topic.conversations.slice(0, 3);

  return (
    <section className="rounded-2xl border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-glass)] p-3 sm:p-4" aria-label={topic.topicLabel}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2 py-1 text-xs text-[color:var(--color-text-muted)]">
            <Tag className="h-3.5 w-3.5" aria-hidden="true" />
            {topic.topicLabel}
          </span>
          {topic.summary ? <p className="text-sm text-[color:var(--color-text-muted)]">{topic.summary}</p> : null}
          <div className="flex flex-wrap items-center gap-3 text-xs text-[color:var(--color-text-muted)]">
            <span className="inline-flex items-center gap-1">
              <MessageSquareText className="h-3.5 w-3.5" aria-hidden="true" />
              {formatConversationCount(topic.conversations.length, messages.topicConversationCountLabel)}
            </span>
            {latestActivity ? (
              <span className="inline-flex items-center gap-1">
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                {messages.topicLatestActivityLabel}: {latestActivity}
              </span>
            ) : null}
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => onOpenTopic(topic)} className="min-h-11">
          {messages.openTopicAction}
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      <div className="mt-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">{messages.recentConversationsLabel}</p>
        <ul className="space-y-2">
          {recentConversations.map((record) => (
            <TopicConversationRow
              key={record.id}
              record={record}
              locale={locale}
              onOpenConversation={(conversation) => onOpenConversation(topic, conversation)}
              labels={labels}
            />
          ))}
        </ul>
      </div>
    </section>
  );
}

function HistoryTopicList({
  topics,
  locale,
  onOpenTopic,
  onOpenConversation,
  labels,
  messages
}: {
  topics: ConversationTopicGroup[];
  locale: string;
  onOpenTopic: (topic: ConversationTopicGroup) => void;
  onOpenConversation: (topic: ConversationTopicGroup, conversation: ConversationHistoryItem) => void;
  labels: {
    openConversationAria: string;
    statusActive: string;
    statusArchived: string;
    untitledConversation: string;
    noPreview: string;
  };
  messages: ReturnType<typeof useI18n>["messages"]["history"];
}) {
  return (
    <MotionList className="grid gap-3 lg:grid-cols-2" aria-label={messages.topicGroupsAriaLabel}>
      {topics.map((topic) => (
        <MotionListItem key={topic.topicId}>
          <HistoryTopicGroupCard
            topic={topic}
            locale={locale}
            onOpenTopic={onOpenTopic}
            onOpenConversation={onOpenConversation}
            labels={labels}
            messages={messages}
          />
        </MotionListItem>
      ))}
    </MotionList>
  );
}

export function EmptyHistoryState({ title, description }: { title: string; description: string }) {
  return <EmptyState title={title} description={description} />;
}

export function ConversationHistoryPage() {
  const navigate = useNavigate();
  const { locale, messages } = useI18n();
  const startHistoryChoice = useChatEntryFlowStore((state) => state.startHistoryChoice);

  const [status, setStatus] = useState<HistoryLoadStatus>("loading");
  const [topics, setTopics] = useState<ConversationTopicGroup[]>([]);
  const [query, setQuery] = useState("");

  const loadHistory = async () => {
    setStatus("loading");
    try {
      const response = await historyService.listConversationHistory();
      setTopics(groupConversationHistoryByTopic(response));
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    void loadHistory();
  }, []);

  const filteredTopics = useMemo(() => {
    const normalizedQuery = normalizeSearchValue(query);
    if (!normalizedQuery) return topics;
    return topics.filter((topic) => topicGroupMatchesQuery(topic, normalizedQuery));
  }, [query, topics]);

  const hasData = filteredTopics.length > 0;
  const isSearchActive = query.trim().length > 0;

  const handleNavigateToChat = (payload: HistoryChatEntryNavigationState) => {
    startHistoryChoice({
      selectedTopicId: payload.selectedTopicId,
      selectedTopicLabel: payload.selectedTopicLabel,
      selectedConversationId: payload.selectedConversationId
    });
    navigate(appRoutes.agent, { state: payload });
  };

  const handleOpenTopic = (topic: ConversationTopicGroup) => {
    const latestConversationId = topic.conversations[0]?.conversationId ?? null;
    handleNavigateToChat({
      source: "history",
      chatEntryMode: "history-choice",
      selectedTopicId: topic.topicId,
      selectedTopicLabel: topic.topicLabel,
      selectedConversationId: latestConversationId
    });
  };

  const handleOpenConversation = (topic: ConversationTopicGroup, conversation: ConversationHistoryItem) => {
    handleNavigateToChat({
      source: "history",
      chatEntryMode: "history-choice",
      selectedTopicId: topic.topicId,
      selectedTopicLabel: topic.topicLabel,
      selectedConversationId: conversation.conversationId
    });
  };

  return (
    <ScreenShell>
      <PageContainer className="py-8 sm:py-10">
        <MotionPage>
        <SectionContainer className="mx-auto w-full max-w-4xl space-y-4">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className={dsTypography.pageTitle}>{messages.history.pageTitle}</h1>
              <p className="mt-1 text-sm text-muted-foreground">{messages.history.pageSubtitle}</p>
            </div>
            <Link to={appRoutes.agent}>
              <Button variant="secondary" size="md">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                {messages.history.backToChat}
              </Button>
            </Link>
          </header>

          <HistorySearch
            query={query}
            onChange={setQuery}
            onClear={() => setQuery("")}
            placeholder={messages.history.searchPlaceholder}
            ariaLabel={messages.history.searchAriaLabel}
            clearLabel={messages.history.clearSearch}
          />

          <CardShell className="p-3 sm:p-4">
            {status === "loading" ? (
              <div role="status" aria-live="polite" aria-label={messages.history.loadingLabel}>
                <LoadingSkeleton lines={6} />
              </div>
            ) : null}

            {status === "error" ? (
              <ErrorPanel
                title={messages.history.errorTitle}
                message={messages.history.errorMessage}
                retryLabel={messages.history.retry}
                onRetry={() => {
                  void loadHistory();
                }}
              />
            ) : null}

            {status === "success" && !hasData ? (
              <EmptyHistoryState
                title={isSearchActive ? messages.history.emptySearchTitle : messages.history.emptyTitle}
                description={isSearchActive ? messages.history.emptySearchDescription : messages.history.emptyDescription}
              />
            ) : null}

            {status === "success" && hasData ? (
              <HistoryTopicList
                topics={filteredTopics}
                locale={locale}
                onOpenTopic={handleOpenTopic}
                onOpenConversation={handleOpenConversation}
                labels={{
                  openConversationAria: messages.history.openConversationAria,
                  statusActive: messages.history.statusActive,
                  statusArchived: messages.history.statusArchived,
                  untitledConversation: messages.history.untitledConversation,
                  noPreview: messages.history.noPreview
                }}
                messages={messages.history}
              />
            ) : null}
          </CardShell>
        </SectionContainer>
        </MotionPage>
      </PageContainer>
    </ScreenShell>
  );
}
