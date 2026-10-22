import { create } from "zustand";
import type {
  AgentMemoryEnrichmentPayload,
  ReferralChatMessage,
  ReferralChatThreadSummary,
  ReferralDashboardStats,
  ReferralLinkSummary,
  ReferralPersonalizationProfile,
  ReferralProgressEvent,
  ReferralTagColor,
} from "@/services/referral";

export interface ReferralDraftLink {
  label: string;
  color: ReferralTagColor;
}

interface ReferralState {
  status: "idle" | "loading" | "success" | "error";
  stats: ReferralDashboardStats | null;
  links: ReferralLinkSummary[];
  progressEventsByLinkId: Record<string, ReferralProgressEvent[]>;
  chatThreadByLinkId: Record<string, ReferralChatThreadSummary>;
  personalizationByLinkId: Record<string, ReferralPersonalizationProfile>;
  memorySyncByLinkId: Record<string, AgentMemoryEnrichmentPayload>;
  draft: ReferralDraftLink | null;
  expandedStatusByLinkId: Record<string, boolean>;
}

interface ReferralActions {
  setStatus: (status: ReferralState["status"]) => void;
  setStats: (stats: ReferralDashboardStats | null) => void;
  setLinks: (links: ReferralLinkSummary[]) => void;
  prependLink: (link: ReferralLinkSummary) => void;
  updateLink: (linkId: string, partial: Partial<ReferralLinkSummary>) => void;
  setProgressEvents: (linkId: string, events: ReferralProgressEvent[]) => void;
  setChatThread: (linkId: string, thread: ReferralChatThreadSummary) => void;
  appendChatMessage: (linkId: string, message: ReferralChatMessage) => void;
  setPersonalizationProfile: (linkId: string, profile: ReferralPersonalizationProfile) => void;
  setMemorySyncPayload: (linkId: string, payload: AgentMemoryEnrichmentPayload) => void;
  setDraft: (draft: ReferralDraftLink | null) => void;
  patchDraft: (partial: Partial<ReferralDraftLink>) => void;
  setStatusPanelExpanded: (linkId: string, expanded: boolean) => void;
  reset: () => void;
}

export type ReferralStore = ReferralState & ReferralActions;

const initialState: ReferralState = {
  status: "idle",
  stats: null,
  links: [],
  progressEventsByLinkId: {},
  chatThreadByLinkId: {},
  personalizationByLinkId: {},
  memorySyncByLinkId: {},
  draft: null,
  expandedStatusByLinkId: {},
};

export const useReferralStore = create<ReferralStore>((set) => ({
  ...initialState,
  setStatus: (status) => set({ status }),
  setStats: (stats) => set({ stats }),
  setLinks: (links) => set({ links: [...links] }),
  prependLink: (link) => set((state) => ({ links: [link, ...state.links.filter((item) => item.id !== link.id)] })),
  updateLink: (linkId, partial) =>
    set((state) => ({
      links: state.links.map((item) => (item.id === linkId ? { ...item, ...partial, id: item.id } : item)),
    })),
  setProgressEvents: (linkId, events) =>
    set((state) => ({
      progressEventsByLinkId: {
        ...state.progressEventsByLinkId,
        [linkId]: [...events],
      },
    })),
  setChatThread: (linkId, thread) =>
    set((state) => ({
      chatThreadByLinkId: {
        ...state.chatThreadByLinkId,
        [linkId]: {
          ...thread,
          messages: [...thread.messages],
        },
      },
    })),
  appendChatMessage: (linkId, message) =>
    set((state) => {
      const current = state.chatThreadByLinkId[linkId];
      if (!current) return state;
      return {
        chatThreadByLinkId: {
          ...state.chatThreadByLinkId,
          [linkId]: {
            ...current,
            latestMessageAt: message.createdAt,
            messages: [...current.messages, message],
          },
        },
      };
    }),
  setPersonalizationProfile: (linkId, profile) =>
    set((state) => ({
      personalizationByLinkId: {
        ...state.personalizationByLinkId,
        [linkId]: profile,
      },
    })),
  setMemorySyncPayload: (linkId, payload) =>
    set((state) => ({
      memorySyncByLinkId: {
        ...state.memorySyncByLinkId,
        [linkId]: payload,
      },
    })),
  setDraft: (draft) => set({ draft }),
  patchDraft: (partial) =>
    set((state) => ({
      draft: state.draft
        ? {
            ...state.draft,
            ...partial,
          }
        : state.draft,
    })),
  setStatusPanelExpanded: (linkId, expanded) =>
    set((state) => ({
      expandedStatusByLinkId: {
        ...state.expandedStatusByLinkId,
        [linkId]: expanded,
      },
    })),
  reset: () => set(initialState),
}));
