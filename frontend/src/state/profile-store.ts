import { create } from "zustand";

interface ProfileSummary {
  userId: string | null;
  fullName: string | null;
  email: string | null;
  language: string;
  timezone: string | null;
  activationStatus: "unknown" | "active" | "inactive";
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
  isActivated: boolean;
  eid: string | null;
}

interface ProfileState {
  summary: ProfileSummary | null;
  status: "idle" | "loading" | "success" | "error";
}

interface ProfileActions {
  setSummary: (summary: ProfileSummary | null) => void;
  setStatus: (status: ProfileState["status"]) => void;
  reset: () => void;
}

export type ProfileStore = ProfileState & ProfileActions;

const initialState: ProfileState = {
  summary: null,
  status: "idle"
};

export const useProfileStore = create<ProfileStore>((set) => ({
  ...initialState,
  setSummary: (summary) => set({ summary }),
  setStatus: (status) => set({ status }),
  reset: () => set(initialState)
}));
