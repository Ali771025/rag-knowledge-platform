import { create } from "zustand";

interface ChatComposerDraftState {
  draft: string;
}

interface ChatComposerDraftActions {
  setDraft: (draft: string) => void;
  clearDraft: () => void;
}

export type ChatComposerDraftStore = ChatComposerDraftState & ChatComposerDraftActions;

export const useChatComposerDraftStore = create<ChatComposerDraftStore>((set) => ({
  draft: "",
  setDraft: (draft) => set({ draft }),
  clearDraft: () => set({ draft: "" })
}));

