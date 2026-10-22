import { create } from "zustand";
import type { ChatMessage, Conversation, ConversationMetadata } from "@/types";
import {
  workspaceConversationRepository,
  type CreateConversationInput as RepositoryCreateConversationInput
} from "@/core/workspace/repositories";
import { createLocalStorageAdapter } from "./workspace-storage";

interface LegacyConversationsPersistedState {
  conversations: Conversation[];
  activeConversationId: string | null;
}

interface ActiveConversationPersistedState {
  activeConversationId: string | null;
}

interface ConversationListOptions {
  includeArchived?: boolean;
  includeDeleted?: boolean;
}

interface CreateConversationInput extends RepositoryCreateConversationInput {
  id?: string;
  title?: string;
  projectId?: string | null;
  messages?: ChatMessage[];
  metadata?: ConversationMetadata;
}

export interface WorkspaceConversationsState {
  conversations: Conversation[];
  activeConversationId: string | null;
}

export interface WorkspaceConversationsActions {
  listConversations: (options?: ConversationListOptions) => Conversation[];
  getConversationById: (conversationId: string) => Conversation | null;
  getActiveConversation: () => Conversation | null;
  setActiveConversation: (conversationId: string) => void;
  createConversation: (input?: CreateConversationInput) => string;
  renameConversation: (conversationId: string, title: string) => void;
  archiveConversation: (conversationId: string) => void;
  unarchiveConversation: (conversationId: string) => void;
  setConversationPinned: (conversationId: string, isPinned: boolean) => void;
  deleteConversation: (conversationId: string) => void;
  appendMessage: (conversationId: string, message: ChatMessage) => void;
  updateMessage: (conversationId: string, messageId: string, partial: Partial<ChatMessage>) => void;
  setConversationMessages: (conversationId: string, messages: ChatMessage[]) => void;
  setConversationProject: (conversationId: string, projectId: string | null) => void;
}

export type WorkspaceConversationsStore = WorkspaceConversationsState & WorkspaceConversationsActions;

const LEGACY_STORAGE_KEY = "ragai.workspace.conversations.v1";
const ACTIVE_CONVERSATION_STORAGE_KEY = "ragai.workspace.active-conversation.v1";

const legacyStorage = createLocalStorageAdapter<LegacyConversationsPersistedState>(LEGACY_STORAGE_KEY);
const activeConversationStorage = createLocalStorageAdapter<ActiveConversationPersistedState>(ACTIVE_CONVERSATION_STORAGE_KEY);

function ensureConversations(): Conversation[] {
  const list = workspaceConversationRepository.listConversations();
  if (list.length > 0) {
    return list;
  }

  const created = workspaceConversationRepository.createConversation();
  return [created];
}

function resolveInitialActiveConversationId(conversations: Conversation[]): string | null {
  const fromNewStorage = activeConversationStorage.load()?.activeConversationId;
  if (fromNewStorage && conversations.some((conversation) => conversation.id === fromNewStorage)) {
    return fromNewStorage;
  }

  const fromLegacyStorage = legacyStorage.load()?.activeConversationId;
  if (fromLegacyStorage && conversations.some((conversation) => conversation.id === fromLegacyStorage)) {
    return fromLegacyStorage;
  }

  const fallback =
    conversations.find((conversation) => conversation.status === "active") ??
    conversations.find((conversation) => conversation.status === "archived") ??
    null;
  return fallback?.id ?? null;
}

function persistActiveConversationId(activeConversationId: string | null) {
  activeConversationStorage.save({ activeConversationId });
}

function refreshConversationsFromRepository(): Conversation[] {
  return workspaceConversationRepository.listConversations();
}

const initialConversations = ensureConversations();
const initialActiveConversationId = resolveInitialActiveConversationId(initialConversations);

if (initialActiveConversationId) {
  persistActiveConversationId(initialActiveConversationId);
}

const initialState: WorkspaceConversationsState = {
  conversations: initialConversations,
  activeConversationId: initialActiveConversationId
};

export const useWorkspaceConversationsStore = create<WorkspaceConversationsStore>((set, get) => ({
  ...initialState,
  listConversations: (options) => {
    const includeArchived = options?.includeArchived ?? true;
    const includeDeleted = options?.includeDeleted ?? false;

    return get().conversations.filter((conversation) => {
      if (!includeDeleted && conversation.status === "deleted") return false;
      if (!includeArchived && conversation.status === "archived") return false;
      return true;
    });
  },
  getConversationById: (conversationId) => {
    if (!conversationId) return null;
    return get().conversations.find((conversation) => conversation.id === conversationId) ?? null;
  },
  getActiveConversation: () => {
    const state = get();
    if (!state.activeConversationId) return null;
    return state.conversations.find((conversation) => conversation.id === state.activeConversationId) ?? null;
  },
  setActiveConversation: (conversationId) => {
    if (!conversationId) return;

    set((state) => {
      if (state.activeConversationId === conversationId) {
        return state;
      }
      const target = state.conversations.find((conversation) => conversation.id === conversationId);
      if (!target) return state;

      persistActiveConversationId(conversationId);
      return {
        ...state,
        activeConversationId: conversationId
      };
    });
  },
  createConversation: (input) => {
    const created = workspaceConversationRepository.createConversation(input);
    const conversations = refreshConversationsFromRepository();

    set({
      conversations,
      activeConversationId: created.id
    });
    persistActiveConversationId(created.id);

    return created.id;
  },
  renameConversation: (conversationId, title) => {
    const trimmed = title.trim();
    if (!conversationId || !trimmed) return;

    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      title: trimmed
    });
    if (!updated) return;

    set((state) => ({
      ...state,
      conversations: refreshConversationsFromRepository()
    }));
  },
  archiveConversation: (conversationId) => {
    if (!conversationId) return;
    const archived = workspaceConversationRepository.archiveConversation(conversationId);
    if (!archived) return;

    set((state) => {
      const conversations = refreshConversationsFromRepository();
      let activeConversationId = state.activeConversationId;

      if (state.activeConversationId === conversationId) {
        const fallbackActive = conversations.find((conversation) => conversation.status === "active") ?? null;
        if (fallbackActive) {
          activeConversationId = fallbackActive.id;
        } else {
          const created = workspaceConversationRepository.createConversation();
          activeConversationId = created.id;
          conversations.unshift(created);
        }
      }

      persistActiveConversationId(activeConversationId);
      return {
        conversations,
        activeConversationId
      };
    });
  },
  unarchiveConversation: (conversationId) => {
    if (!conversationId) return;

    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      status: "active",
      archivedAt: undefined
    });
    if (!updated) return;

    set((state) => {
      const conversations = refreshConversationsFromRepository();
      const activeConversationId = state.activeConversationId ?? updated.id;
      if (!state.activeConversationId) {
        persistActiveConversationId(activeConversationId);
      }
      return {
        conversations,
        activeConversationId
      };
    });
  },
  setConversationPinned: (conversationId, isPinned) => {
    if (!conversationId) return;

    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      isPinned,
      updatedAt: new Date().toISOString()
    });
    if (!updated) return;

    set((state) => ({
      ...state,
      conversations: refreshConversationsFromRepository()
    }));
  },
  deleteConversation: (conversationId) => {
    if (!conversationId) return;
    const deleted = workspaceConversationRepository.deleteConversation(conversationId);
    if (!deleted) return;

    set((state) => {
      let conversations = refreshConversationsFromRepository();
      let activeConversationId = state.activeConversationId;

      if (state.activeConversationId === conversationId) {
        const fallback =
          conversations.find((conversation) => conversation.status === "active") ??
          conversations.find((conversation) => conversation.status === "archived") ??
          null;
        activeConversationId = fallback?.id ?? null;
      }

      if (conversations.length === 0) {
        const created = workspaceConversationRepository.createConversation();
        conversations = [created];
        activeConversationId = created.id;
      }

      persistActiveConversationId(activeConversationId);
      return {
        conversations,
        activeConversationId
      };
    });
  },
  appendMessage: (conversationId, message) => {
    if (!conversationId) return;
    const target = get().conversations.find((conversation) => conversation.id === conversationId);
    if (!target) return;

    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      messages: [...target.messages, message]
    });
    if (!updated) return;

    set((state) => ({
      ...state,
      conversations: refreshConversationsFromRepository()
    }));
  },
  updateMessage: (conversationId, messageId, partial) => {
    if (!conversationId || !messageId) return;
    const target = get().conversations.find((conversation) => conversation.id === conversationId);
    if (!target) return;

    const hasMessage = target.messages.some((message) => message.id === messageId);
    if (!hasMessage) return;

    const nextMessages = target.messages.map((message) =>
      message.id === messageId
        ? {
            ...message,
            ...partial,
            id: message.id
          }
        : message
    );
    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      messages: nextMessages
    });
    if (!updated) return;

    set((state) => ({
      ...state,
      conversations: refreshConversationsFromRepository()
    }));
  },
  setConversationMessages: (conversationId, messages) => {
    if (!conversationId) return;
    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      messages: [...messages]
    });
    if (!updated) return;

    set((state) => ({
      ...state,
      conversations: refreshConversationsFromRepository()
    }));
  },
  setConversationProject: (conversationId, projectId) => {
    if (!conversationId) return;
    const updated = workspaceConversationRepository.updateConversation(conversationId, {
      projectId
    });
    if (!updated) return;

    set((state) => ({
      ...state,
      conversations: refreshConversationsFromRepository()
    }));
  }
}));
