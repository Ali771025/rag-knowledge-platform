import { requestApi } from "./client";

export interface DashboardCardActionResponse {
  label_key: "goToChat" | "openProfile" | "openChat" | "openReferral" | "openHistory";
  href: string;
  enabled: boolean;
}

export interface DashboardCardResponse {
  id: string;
  title_key: "activationOverview" | "conversationHub" | "networkGrowth" | "historyReview";
  summary_key:
    | "activationOverviewActiveSummary"
    | "activationOverviewPendingSummary"
    | "conversationHubSummary"
    | "networkGrowthSummary"
    | "historyReviewSummary";
  status: "idle" | "in_progress" | "complete" | "blocked";
  action: DashboardCardActionResponse | null;
  icon_key?: "chat" | "profile" | "referral" | "history" | null;
  progress?: number | null;
  priority?: "low" | "medium" | "high" | null;
}

export interface DashboardActivationResponse {
  is_activated: boolean;
  onboarding_progress: number;
  initial_interaction_completed: boolean;
  registration_completed: boolean;
  first_tasks_received: boolean;
}

export interface DashboardCardsResponse {
  activation: DashboardActivationResponse;
  cards: DashboardCardResponse[];
}

const DASHBOARD_API_ENDPOINTS = {
  cards: "/v1/dashboard/cards"
} as const;

export async function getDashboardCards(): Promise<DashboardCardsResponse> {
  return requestApi<DashboardCardsResponse>({
    method: "GET",
    url: DASHBOARD_API_ENDPOINTS.cards
  });
}
