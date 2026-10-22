import { appRoutes } from "@/app/routes/contracts";
import { getDashboardCards, isApiClientError } from "@/core/api";
import type { DashboardCard, DashboardCardStatus } from "@/state/dashboard-store";

export interface DashboardActivationSnapshot {
  isActivated: boolean;
  onboardingProgress: number;
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}

export interface DashboardSnapshot {
  activation: DashboardActivationSnapshot;
  cards: DashboardCard[];
}

export interface DashboardService {
  getSnapshot: (input: {
    isActivated: boolean;
    initialInteractionCompleted: boolean;
    registrationCompleted: boolean;
    firstTasksReceived: boolean;
  }) => Promise<DashboardSnapshot>;
}

function activationProgress(input: {
  isActivated: boolean;
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}): number {
  const score =
    Number(input.initialInteractionCompleted) +
    Number(input.registrationCompleted) +
    Number(input.firstTasksReceived) +
    Number(input.isActivated);
  return Math.round((score / 4) * 100);
}

class LocalDashboardService implements DashboardService {
  async getSnapshot(input: {
    isActivated: boolean;
    initialInteractionCompleted: boolean;
    registrationCompleted: boolean;
    firstTasksReceived: boolean;
  }): Promise<DashboardSnapshot> {
    const progress = activationProgress(input);
    const onboardingStatus: DashboardCardStatus = input.isActivated ? "complete" : "in_progress";

    const cards: DashboardCard[] = [
      {
        id: "activation-overview",
        titleKey: "activationOverview",
        summaryKey: input.isActivated ? "activationOverviewActiveSummary" : "activationOverviewPendingSummary",
        status: onboardingStatus,
        action: input.isActivated
          ? { labelKey: "goToChat", href: appRoutes.agent, enabled: true }
          : { labelKey: "openProfile", href: appRoutes.profile, enabled: true },
        iconKey: "profile",
        progress,
        priority: input.isActivated ? "low" : "high"
      },
      {
        id: "conversation-flow",
        titleKey: "conversationHub",
        summaryKey: "conversationHubSummary",
        status: "idle",
        action: { labelKey: "openChat", href: appRoutes.agent, enabled: true },
        iconKey: "chat",
        priority: "medium"
      },
      {
        id: "network-growth",
        titleKey: "networkGrowth",
        summaryKey: "networkGrowthSummary",
        status: "idle",
        action: { labelKey: "openReferral", href: appRoutes.referral, enabled: true },
        iconKey: "referral",
        priority: "low"
      },
      {
        id: "history-review",
        titleKey: "historyReview",
        summaryKey: "historyReviewSummary",
        status: "idle",
        action: { labelKey: "openHistory", href: appRoutes.history, enabled: true },
        iconKey: "history",
        priority: "low"
      }
    ];

    return {
      activation: {
        isActivated: input.isActivated,
        onboardingProgress: progress,
        initialInteractionCompleted: input.initialInteractionCompleted,
        registrationCompleted: input.registrationCompleted,
        firstTasksReceived: input.firstTasksReceived
      },
      cards
    };
  }
}

class ApiDashboardService implements DashboardService {
  async getSnapshot(input: {
    isActivated: boolean;
    initialInteractionCompleted: boolean;
    registrationCompleted: boolean;
    firstTasksReceived: boolean;
  }): Promise<DashboardSnapshot> {
    try {
      const response = await getDashboardCards();
      return {
        activation: {
          isActivated: response.activation.is_activated,
          onboardingProgress: response.activation.onboarding_progress,
          initialInteractionCompleted: response.activation.initial_interaction_completed,
          registrationCompleted: response.activation.registration_completed,
          firstTasksReceived: response.activation.first_tasks_received
        },
        cards: response.cards.map((card) => ({
          id: card.id,
          titleKey: card.title_key,
          summaryKey: card.summary_key,
          status: card.status,
          action: card.action
            ? {
                labelKey: card.action.label_key,
                href: card.action.href,
                enabled: card.action.enabled
              }
            : null,
          iconKey: card.icon_key ?? undefined,
          progress: typeof card.progress === "number" ? card.progress : undefined,
          priority: card.priority ?? undefined
        }))
      };
    } catch (error) {
      if (isApiClientError(error) && (error.status === 401 || error.status === 403 || error.status === 404)) {
        const fallback = new LocalDashboardService();
        return fallback.getSnapshot(input);
      }
      throw error;
    }
  }
}

export const dashboardService: DashboardService = new ApiDashboardService();
