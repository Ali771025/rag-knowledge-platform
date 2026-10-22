import { create } from "zustand";
import type { FunnelStage } from "@/types";

interface FunnelState {
  stage: FunnelStage;
  score: number | null;
}

interface FunnelActions {
  setStage: (stage: FunnelStage) => void;
  setScore: (score: number | null) => void;
  reset: () => void;
}

export type FunnelStore = FunnelState & FunnelActions;

const initialState: FunnelState = {
  stage: "ENTRY",
  score: null
};

export const useFunnelStore = create<FunnelStore>((set) => ({
  ...initialState,
  setStage: (stage) => set({ stage }),
  setScore: (score) => set({ score: Number.isFinite(score) ? score : null }),
  reset: () => set(initialState)
}));

