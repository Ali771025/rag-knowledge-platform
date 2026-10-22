import { create } from "zustand";

interface VoiceSessionState {
  sessionId: string | null;
  status: "idle" | "recording" | "processing" | "speaking" | "error" | "permission_denied";
  startedAt: string | null;
  endedAt: string | null;
}

interface VoiceSessionActions {
  start: (sessionId: string) => void;
  setStatus: (status: VoiceSessionState["status"]) => void;
  complete: () => void;
  reset: () => void;
}

export type VoiceSessionStore = VoiceSessionState & VoiceSessionActions;

const initialState: VoiceSessionState = {
  sessionId: null,
  status: "idle",
  startedAt: null,
  endedAt: null
};

function nowIso(): string {
  return new Date().toISOString();
}

export const useVoiceSessionStore = create<VoiceSessionStore>((set) => ({
  ...initialState,
  start: (sessionId) =>
    set({
      sessionId: sessionId.trim(),
      status: "recording",
      startedAt: nowIso(),
      endedAt: null
    }),
  setStatus: (status) => set({ status }),
  complete: () => set((state) => ({ ...state, status: "idle", endedAt: nowIso() })),
  reset: () => set(initialState)
}));
