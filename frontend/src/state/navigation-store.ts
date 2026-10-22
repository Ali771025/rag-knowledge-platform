import { create } from "zustand";

interface NavigationState {
  pendingDestination: string | null;
}

interface NavigationActions {
  setPendingDestination: (path: string | null) => void;
  clearPendingDestination: () => void;
}

export type NavigationStore = NavigationState & NavigationActions;

export const useNavigationStore = create<NavigationStore>((set) => ({
  pendingDestination: null,
  setPendingDestination: (pendingDestination) => {
    set({ pendingDestination: pendingDestination?.trim() || null });
  },
  clearPendingDestination: () => {
    set({ pendingDestination: null });
  }
}));

