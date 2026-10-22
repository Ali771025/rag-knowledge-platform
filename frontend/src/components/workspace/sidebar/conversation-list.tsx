import { useMemo } from "react";
import type { Conversation } from "@/types";
import { useAnalytics } from "@/hooks/use-analytics";
import { useWorkspaceConversationsStore, useWorkspaceUiStore } from "@/state";
import { ConversationListItem } from "./conversation-list-item";

interface ConversationListProps {
  compact: boolean;
  onAfterSelect?: () => void;
}

interface ConversationSection {
  key: string;
  label: string;
  items: Conversation[];
}

function bucketByRecency(conversation: Conversation): "today" | "yesterday" | "last_7_days" | "last_30_days" | "older" {
  const updated = new Date(conversation.updatedAt).getTime();
  const now = Date.now();
  const dayMs = 24 * 60 * 60 * 1000;
  const daysAgo = Math.floor((now - updated) / dayMs);

  if (daysAgo <= 0) return "today";
  if (daysAgo === 1) return "yesterday";
  if (daysAgo <= 7) return "last_7_days";
  if (daysAgo <= 30) return "last_30_days";
  return "older";
}

export function ConversationList({ compact, onAfterSelect }: ConversationListProps) {
  const { trackConversationSelected } = useAnalytics();
  const conversations = useWorkspaceConversationsStore((state) => state.conversations);
  const activeConversationId = useWorkspaceConversationsStore((state) => state.activeConversationId);
  const setActiveConversation = useWorkspaceConversationsStore((state) => state.setActiveConversation);
  const searchQuery = useWorkspaceUiStore((state) => state.searchQuery);
  const currentView = useWorkspaceUiStore((state) => state.currentView);
  const activeProjectId = useWorkspaceUiStore((state) => state.activeProjectId);

  const scopedConversations = useMemo(() => {
    return conversations
      .filter((conversation) => {
        if (conversation.status === "deleted") return false;
        if (currentView === "archived") return conversation.status === "archived";
        if (currentView === "project") {
          if (conversation.status !== "active") return false;
          if (activeProjectId === null) return conversation.projectId === null || conversation.projectId === undefined;
          return conversation.projectId === activeProjectId;
        }

        return conversation.status === "active";
      })
      .sort((a, b) => {
        const pinDelta = Number(Boolean(b.isPinned)) - Number(Boolean(a.isPinned));
        if (pinDelta !== 0) return pinDelta;
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      });
  }, [activeProjectId, conversations, currentView]);

  const visibleConversations = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return scopedConversations;
    }

    return scopedConversations.filter((conversation) => conversation.title.toLowerCase().includes(normalizedQuery));
  }, [scopedConversations, searchQuery]);

  const conversationIndexLookup = useMemo(() => {
    const lookup = new Map<string, number>();
    visibleConversations.forEach((conversation, index) => {
      lookup.set(conversation.id, index);
    });
    return lookup;
  }, [visibleConversations]);

  const sections = useMemo<ConversationSection[]>(() => {
    if (currentView === "archived") {
      return [
        {
          key: "archived",
          label: "Archived",
          items: visibleConversations,
        },
      ];
    }

    const pinned = visibleConversations.filter((conversation) => Boolean(conversation.isPinned));
    const unpinned = visibleConversations.filter((conversation) => !conversation.isPinned);
    const bucketed: Record<"today" | "yesterday" | "last_7_days" | "last_30_days" | "older", Conversation[]> = {
      today: [],
      yesterday: [],
      last_7_days: [],
      last_30_days: [],
      older: [],
    };

    unpinned.forEach((conversation) => {
      bucketed[bucketByRecency(conversation)].push(conversation);
    });

    const nextSections: ConversationSection[] = [];
    if (pinned.length > 0) {
      nextSections.push({ key: "pinned", label: "Pinned", items: pinned });
    }
    if (bucketed.today.length > 0) {
      nextSections.push({ key: "today", label: "Today", items: bucketed.today });
    }
    if (bucketed.yesterday.length > 0) {
      nextSections.push({ key: "yesterday", label: "Yesterday", items: bucketed.yesterday });
    }
    if (bucketed.last_7_days.length > 0) {
      nextSections.push({ key: "last_7_days", label: "Previous 7 days", items: bucketed.last_7_days });
    }
    if (bucketed.last_30_days.length > 0) {
      nextSections.push({ key: "last_30_days", label: "Previous 30 days", items: bucketed.last_30_days });
    }
    if (bucketed.older.length > 0) {
      nextSections.push({ key: "older", label: "Older", items: bucketed.older });
    }

    return nextSections;
  }, [currentView, visibleConversations]);

  if (compact) {
    return null;
  }

  const isSearching = searchQuery.trim().length > 0;
  const hasScopedConversations = scopedConversations.length > 0;

  return (
    <section className="space-y-2" aria-label="Conversations">
      <h3 className="px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {currentView === "archived" ? "Archived conversations" : "Conversations"}
      </h3>
      <div className="space-y-3" aria-label={currentView === "archived" ? "Archived conversations" : "Active conversations"}>
        {sections.map((section) => (
          <div key={section.key} className="space-y-1">
            <h4 className="px-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">{section.label}</h4>
            <div className="space-y-1">
              {section.items.map((conversation) => (
                <ConversationListItem
                  key={conversation.id}
                  conversation={conversation}
                  active={conversation.id === activeConversationId}
                  onSelect={() => {
                    setActiveConversation(conversation.id);
                    trackConversationSelected(conversation.id, conversationIndexLookup.get(conversation.id) ?? 0);
                    onAfterSelect?.();
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      {visibleConversations.length === 0 && !isSearching && !hasScopedConversations ? (
        <p className="px-2 text-xs text-slate-500">
          {currentView === "archived"
            ? "No archived conversations yet."
            : currentView === "project"
              ? "No conversations in this scope."
              : "No conversations yet. Start a new chat."}
        </p>
      ) : null}
      {visibleConversations.length === 0 && isSearching ? (
        <p className="px-2 text-xs text-slate-500">No conversations match your search.</p>
      ) : null}
    </section>
  );
}
