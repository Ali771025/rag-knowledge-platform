import { create } from "zustand";
import { createLocalStorageAdapter } from "./workspace-storage";

type ActivationStatus = "unknown" | "active" | "inactive";

interface ActivationState {
  status: ActivationStatus;
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}

interface ActivationActions {
  setStatus: (status: ActivationStatus) => void;
  setInitialInteractionCompleted: (value: boolean) => void;
  setRegistrationCompleted: (value: boolean) => void;
  setFirstTasksReceived: (value: boolean) => void;
  hydrate: () => void;
  reset: () => void;
}

export type ActivationStore = ActivationState & ActivationActions;

const STORAGE_KEY = "ragai.activation.v1";

interface ActivationPersistedState {
  status: ActivationStatus;
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}

const activationStorage = createLocalStorageAdapter<ActivationPersistedState>(STORAGE_KEY);

const initialState: ActivationState = {
  status: "unknown",
  initialInteractionCompleted: false,
  registrationCompleted: false,
  firstTasksReceived: false
};

function persistState(state: ActivationState): void {
  activationStorage.save({
    status: state.status,
    initialInteractionCompleted: state.initialInteractionCompleted,
    registrationCompleted: state.registrationCompleted,
    firstTasksReceived: state.firstTasksReceived
  });
}

function loadPersistedState(): ActivationState {
  const persisted = activationStorage.load();
  if (!persisted) {
    return initialState;
  }
  return {
    status: persisted.status,
    initialInteractionCompleted: persisted.initialInteractionCompleted,
    registrationCompleted: persisted.registrationCompleted,
    firstTasksReceived: persisted.firstTasksReceived
  };
}

export const useActivationStore = create<ActivationStore>((set) => ({
  ...loadPersistedState(),
  setStatus: (status) =>
    set((state) => {
      const next = { ...state, status };
      persistState(next);
      return next;
    }),
  setInitialInteractionCompleted: (value) =>
    set((state) => {
      const next = { ...state, initialInteractionCompleted: value };
      persistState(next);
      return next;
    }),
  setRegistrationCompleted: (value) =>
    set((state) => {
      const next = { ...state, registrationCompleted: value };
      persistState(next);
      return next;
    }),
  setFirstTasksReceived: (value) =>
    set((state) => {
      const next = { ...state, firstTasksReceived: value };
      persistState(next);
      return next;
    }),
  hydrate: () => {
    set(loadPersistedState());
  },
  reset: () =>
    set(() => {
      activationStorage.clear();
      return initialState;
    })
}));
