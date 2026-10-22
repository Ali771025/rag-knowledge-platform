import { create } from "zustand";

export type UiError = {
  message: string;
  code?: string;
  source?: "chat" | "session" | "network" | "unknown";
};

export interface UiState {
  isTyping: boolean;
  isStreaming: boolean;
  error: UiError | null;
}

export interface UiActions {
  setTyping: (value: boolean) => void;
  setStreaming: (value: boolean) => void;
  setError: (error: UiError | null) => void;
  clearError: () => void;
  resetUiState: () => void;
}

export type UiStore = UiState & UiActions;

export const initialUiState: UiState = {
  isTyping: false,
  isStreaming: false,
  error: null
};

export const useUiStore = create<UiStore>((set) => ({
  ...initialUiState,
  setTyping: (value) => {
    set((state) => {
      if (state.isTyping === value) {
        return state;
      }
      return { isTyping: value };
    });
  },
  setStreaming: (value) => {
    set((state) => {
      if (state.isStreaming === value) {
        return state;
      }
      return { isStreaming: value };
    });
  },
  setError: (error) => {
    set((state) => {
      const sameError =
        state.error?.message === error?.message &&
        state.error?.code === error?.code &&
        state.error?.source === error?.source;
      if (sameError) {
        return state;
      }
      return { error };
    });
  },
  clearError: () => {
    set((state) => {
      if (state.error === null) {
        return state;
      }
      return { error: null };
    });
  },
  resetUiState: () => {
    set(initialUiState);
  }
}));
