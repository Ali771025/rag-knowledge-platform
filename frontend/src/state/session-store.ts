import { create } from "zustand";
import type { FunnelStage, PersonaType, SessionStateSnapshot, SuggestedAction } from "@/types";

interface SessionState extends SessionStateSnapshot {}

interface SessionActions {
  setSession: (payload: SessionStateSnapshot) => void;
  resetSession: () => void;
  updatePersona: (persona: PersonaType, confidence?: number | null) => void;
  updateTrustScore: (value: number | null) => void;
  updateStage: (stage: FunnelStage) => void;
  setSuggestedActions: (actions: SuggestedAction[]) => void;
  patchSession: (partial: Partial<SessionStateSnapshot>) => void;
}

type SessionStore = SessionState & SessionActions;

export type { SessionState, SessionActions, SessionStore };

export const initialSessionState: SessionState = {
  sessionId: null,
  persona: "UNKNOWN",
  confidence: null,
  trustScore: null,
  funnelStage: "ENTRY",
  suggestedActions: [],
  metadata: undefined
};

function toFiniteNumber(value: number | null): number | null {
  if (value === null) return null;
  return Number.isFinite(value) ? value : null;
}

export const useSessionStore = create<SessionStore>((set) => ({
  ...initialSessionState,
  setSession: (payload) => {
    set({
      ...payload,
      confidence: toFiniteNumber(payload.confidence),
      trustScore: toFiniteNumber(payload.trustScore)
    });
  },
  resetSession: () => {
    set(initialSessionState);
  },
  updatePersona: (persona, confidence) => {
    set((state) => ({
      persona,
      confidence: confidence === undefined ? state.confidence : toFiniteNumber(confidence)
    }));
  },
  updateTrustScore: (value) => {
    set({ trustScore: toFiniteNumber(value) });
  },
  updateStage: (stage) => {
    set({ funnelStage: stage });
  },
  setSuggestedActions: (actions) => {
    set({ suggestedActions: [...actions] });
  },
  patchSession: (partial) => {
    set((state) => ({
      ...state,
      ...partial,
      confidence: partial.confidence === undefined ? state.confidence : toFiniteNumber(partial.confidence),
      trustScore: partial.trustScore === undefined ? state.trustScore : toFiniteNumber(partial.trustScore),
      suggestedActions:
        partial.suggestedActions === undefined ? state.suggestedActions : [...partial.suggestedActions]
    }));
  }
}));
