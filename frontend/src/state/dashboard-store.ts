import { create } from "zustand";

export type DashboardCardStatus = "idle" | "in_progress" | "complete" | "blocked";
export type DashboardCardPriority = "low" | "medium" | "high";
export type DashboardCardTitleKey =
  | "activationOverview"
  | "conversationHub"
  | "networkGrowth"
  | "historyReview";
export type DashboardCardSummaryKey =
  | "activationOverviewActiveSummary"
  | "activationOverviewPendingSummary"
  | "conversationHubSummary"
  | "networkGrowthSummary"
  | "historyReviewSummary";
export type DashboardActionLabelKey = "goToChat" | "openProfile" | "openChat" | "openReferral" | "openHistory";

export interface DashboardCardAction {
  labelKey: DashboardActionLabelKey;
  href: string;
  enabled: boolean;
}

export interface DashboardCard {
  id: string;
  titleKey: DashboardCardTitleKey;
  summaryKey: DashboardCardSummaryKey;
  status: DashboardCardStatus;
  action: DashboardCardAction | null;
  iconKey?: "chat" | "profile" | "referral" | "history";
  progress?: number;
  priority?: DashboardCardPriority;
}

interface DashboardState {
  cards: DashboardCard[];
  status: "idle" | "loading" | "success" | "error";
}

interface DashboardActions {
  setCards: (cards: DashboardCard[]) => void;
  setStatus: (status: DashboardState["status"]) => void;
  reset: () => void;
}

export type DashboardStore = DashboardState & DashboardActions;

const initialState: DashboardState = {
  cards: [],
  status: "idle"
};

export const useDashboardStore = create<DashboardStore>((set) => ({
  ...initialState,
  setCards: (cards) => set({ cards: [...cards] }),
  setStatus: (status) => set({ status }),
  reset: () => set(initialState)
}));
