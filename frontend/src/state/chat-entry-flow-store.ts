import { create } from "zustand";

export type ChatEntryMode = "history-choice" | "continue" | "new";
export type ChatEntrySource = "history";

export interface HistoryChatEntryPayload {
  selectedTopicId: string;
  selectedTopicLabel: string;
  selectedConversationId: string | null;
}

interface ChatEntryFlowState {
  selectedTopicId: string | null;
  selectedTopicLabel: string | null;
  selectedConversationId: string | null;
  chatEntryMode: ChatEntryMode | null;
  chatEntrySource: ChatEntrySource | null;
}

interface ChatEntryFlowActions {
  startHistoryChoice: (payload: HistoryChatEntryPayload) => void;
  setMode: (mode: ChatEntryMode) => void;
  clear: () => void;
}

export type ChatEntryFlowStore = ChatEntryFlowState & ChatEntryFlowActions;

const initialState: ChatEntryFlowState = {
  selectedTopicId: null,
  selectedTopicLabel: null,
  selectedConversationId: null,
  chatEntryMode: null,
  chatEntrySource: null
};

function normalizeValue(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export const useChatEntryFlowStore = create<ChatEntryFlowStore>((set) => ({
  ...initialState,
  startHistoryChoice: (payload) => {
    const selectedTopicId = normalizeValue(payload.selectedTopicId);
    const selectedTopicLabel = normalizeValue(payload.selectedTopicLabel);
    const selectedConversationId = payload.selectedConversationId ? normalizeValue(payload.selectedConversationId) : null;

    if (!selectedTopicId || !selectedTopicLabel) {
      set(initialState);
      return;
    }

    set({
      selectedTopicId,
      selectedTopicLabel,
      selectedConversationId,
      chatEntryMode: "history-choice",
      chatEntrySource: "history"
    });
  },
  setMode: (mode) => {
    set((state) => {
      if (!state.chatEntrySource) {
        return state;
      }
      return {
        ...state,
        chatEntryMode: mode
      };
    });
  },
  clear: () => set(initialState)
}));
