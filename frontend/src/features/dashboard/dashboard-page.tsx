import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CircleDot, CircleOff, CirclePlay, CheckCircle2, History, MessageSquare, UserRound, Users } from "lucide-react";
import { appRoutes } from "@/app/routes/contracts";
import {
  AsyncStatusBadge,
  Button,
  CardShell,
  EmptyState,
  ErrorPanel,
  LoadingSkeleton,
  MotionList,
  MotionListItem,
  MotionPage,
  PageContainer,
  ScreenShell,
  SectionContainer
} from "@/components/ui";
import { dsTypography } from "@/design-system";
import { useI18n } from "@/i18n";
import { dashboardService } from "@/services/dashboard";
import { useActivationStore, useDashboardStore } from "@/state";
import type {
  DashboardActionLabelKey,
  DashboardCard,
  DashboardCardStatus,
  DashboardCardSummaryKey,
  DashboardCardTitleKey
} from "@/state/dashboard-store";

type DashboardLoadStatus = "loading" | "success" | "error";

function statusIcon(status: DashboardCardStatus) {
  switch (status) {
    case "complete":
      return <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />;
    case "in_progress":
      return <CirclePlay className="h-4 w-4 text-accent" aria-hidden="true" />;
    case "blocked":
      return <CircleOff className="h-4 w-4 text-error" aria-hidden="true" />;
    default:
      return <CircleDot className="h-4 w-4 text-muted-foreground" aria-hidden="true" />;
  }
}

function iconForCard(iconKey: DashboardCard["iconKey"]) {
  switch (iconKey) {
    case "chat":
      return <MessageSquare className="h-4 w-4" aria-hidden="true" />;
    case "profile":
      return <UserRound className="h-4 w-4" aria-hidden="true" />;
    case "referral":
      return <Users className="h-4 w-4" aria-hidden="true" />;
    case "history":
      return <History className="h-4 w-4" aria-hidden="true" />;
    default:
      return <CircleDot className="h-4 w-4" aria-hidden="true" />;
  }
}

function toStatusLabel(messages: ReturnType<typeof useI18n>["messages"], status: DashboardCardStatus): string {
  switch (status) {
    case "complete":
      return messages.dashboard.statusComplete;
    case "in_progress":
      return messages.dashboard.statusInProgress;
    case "blocked":
      return messages.dashboard.statusBlocked;
    default:
      return messages.dashboard.statusIdle;
  }
}

function toCardTitle(messages: ReturnType<typeof useI18n>["messages"], key: DashboardCardTitleKey): string {
  const map: Record<DashboardCardTitleKey, string> = {
    activationOverview: messages.dashboard.activationOverviewTitle,
    conversationHub: messages.dashboard.conversationHubTitle,
    networkGrowth: messages.dashboard.networkGrowthTitle,
    historyReview: messages.dashboard.historyReviewTitle
  };
  return map[key];
}

function toCardSummary(messages: ReturnType<typeof useI18n>["messages"], key: DashboardCardSummaryKey): string {
  const map: Record<DashboardCardSummaryKey, string> = {
    activationOverviewActiveSummary: messages.dashboard.activationOverviewActiveSummary,
    activationOverviewPendingSummary: messages.dashboard.activationOverviewPendingSummary,
    conversationHubSummary: messages.dashboard.conversationHubSummary,
    networkGrowthSummary: messages.dashboard.networkGrowthSummary,
    historyReviewSummary: messages.dashboard.historyReviewSummary
  };
  return map[key];
}

function toActionLabel(messages: ReturnType<typeof useI18n>["messages"], key: DashboardActionLabelKey): string {
  const map: Record<DashboardActionLabelKey, string> = {
    goToChat: messages.dashboard.goToChat,
    openProfile: messages.dashboard.openProfile,
    openChat: messages.dashboard.openChat,
    openReferral: messages.dashboard.openReferral,
    openHistory: messages.dashboard.openHistory
  };
  return map[key];
}

function DashboardCardItem({
  card,
  messages
}: {
  card: DashboardCard;
  messages: ReturnType<typeof useI18n>["messages"];
}) {
  const statusLabel = toStatusLabel(messages, card.status);
  const priorityLabel =
    card.priority === "high"
      ? messages.dashboard.priorityHigh
      : card.priority === "medium"
        ? messages.dashboard.priorityMedium
        : messages.dashboard.priorityLow;

  return (
    <CardShell className="p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border bg-muted/30">
              {iconForCard(card.iconKey)}
            </span>
            <h3 className={dsTypography.cardTitle}>{toCardTitle(messages, card.titleKey)}</h3>
          </div>
          <p className="text-sm text-muted-foreground">{toCardSummary(messages, card.summaryKey)}</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/30 px-2 py-0.5 text-[11px] text-muted-foreground">
          {statusIcon(card.status)}
          {statusLabel}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          {messages.dashboard.priorityLabel}: {priorityLabel}
          {typeof card.progress === "number" ? ` · ${messages.dashboard.progressLabel}: ${card.progress}%` : ""}
        </div>
        {card.action && card.action.enabled ? (
          <Link to={card.action.href}>
            <Button variant="secondary" size="sm">
              {toActionLabel(messages, card.action.labelKey)}
            </Button>
          </Link>
        ) : null}
      </div>
    </CardShell>
  );
}

function DashboardCardGrid({
  cards,
  messages
}: {
  cards: DashboardCard[];
  messages: ReturnType<typeof useI18n>["messages"];
}) {
  return (
    <MotionList className="grid gap-3 sm:grid-cols-2">
      {cards.map((card) => (
        <MotionListItem key={card.id}>
          <DashboardCardItem card={card} messages={messages} />
        </MotionListItem>
      ))}
    </MotionList>
  );
}

export function DashboardPage() {
  const { messages } = useI18n();
  const [pageStatus, setPageStatus] = useState<DashboardLoadStatus>("loading");

  const status = useDashboardStore((state) => state.status);
  const cards = useDashboardStore((state) => state.cards);
  const setStatus = useDashboardStore((state) => state.setStatus);
  const setCards = useDashboardStore((state) => state.setCards);

  const activationStatus = useActivationStore((state) => state.status);
  const initialInteractionCompleted = useActivationStore((state) => state.initialInteractionCompleted);
  const registrationCompleted = useActivationStore((state) => state.registrationCompleted);
  const firstTasksReceived = useActivationStore((state) => state.firstTasksReceived);
  const setActivationStatus = useActivationStore((state) => state.setStatus);
  const setInitialInteractionCompleted = useActivationStore((state) => state.setInitialInteractionCompleted);
  const setRegistrationCompleted = useActivationStore((state) => state.setRegistrationCompleted);
  const setFirstTasksReceived = useActivationStore((state) => state.setFirstTasksReceived);
  const isHydratingFromDashboardRef = useRef(false);

  const isActivated = activationStatus === "active";

  const loadDashboard = async () => {
    setStatus("loading");
    setPageStatus("loading");
    try {
      const snapshot = await dashboardService.getSnapshot({
        isActivated,
        initialInteractionCompleted,
        registrationCompleted,
        firstTasksReceived
      });

      const nextStatus = snapshot.activation.isActivated ? "active" : "inactive";
      const nextInitialInteraction = snapshot.activation.initialInteractionCompleted;
      const nextRegistration = snapshot.activation.registrationCompleted;
      const nextFirstTasks = snapshot.activation.firstTasksReceived;

      const hasChange =
        nextStatus !== activationStatus ||
        nextInitialInteraction !== initialInteractionCompleted ||
        nextRegistration !== registrationCompleted ||
        nextFirstTasks !== firstTasksReceived;

      if (hasChange) {
        isHydratingFromDashboardRef.current = true;
        setActivationStatus(nextStatus);
        setInitialInteractionCompleted(nextInitialInteraction);
        setRegistrationCompleted(nextRegistration);
        setFirstTasksReceived(nextFirstTasks);
      }
      setCards(snapshot.cards);
      setStatus("success");
      setPageStatus("success");
    } catch {
      setStatus("error");
      setPageStatus("error");
    }
  };

  useEffect(() => {
    if (isHydratingFromDashboardRef.current) {
      isHydratingFromDashboardRef.current = false;
      return;
    }
    void loadDashboard();
  }, [isActivated, initialInteractionCompleted, registrationCompleted, firstTasksReceived]);

  return (
    <ScreenShell>
      <PageContainer className="py-8 sm:py-10">
        <MotionPage>
        <SectionContainer className="mx-auto w-full max-w-5xl space-y-4">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className={dsTypography.pageTitle}>{messages.dashboard.pageTitle}</h1>
              <p className="mt-1 text-sm text-muted-foreground">{messages.dashboard.pageSubtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              <AsyncStatusBadge status={status === "idle" ? "idle" : status} />
              <Link to={appRoutes.agent}>
                <Button variant="secondary" size="md">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  {messages.dashboard.backToChat}
                </Button>
              </Link>
            </div>
          </header>

          {pageStatus === "loading" ? (
            <CardShell className="p-4">
              <div role="status" aria-live="polite" aria-label={messages.dashboard.loadingLabel}>
                <LoadingSkeleton lines={6} />
              </div>
            </CardShell>
          ) : null}

          {pageStatus === "error" ? (
            <ErrorPanel
              title={messages.dashboard.errorTitle}
              message={messages.dashboard.errorMessage}
              retryLabel={messages.dashboard.retry}
              onRetry={() => {
                void loadDashboard();
              }}
            />
          ) : null}

          {pageStatus === "success" && !isActivated ? (
            <EmptyState title={messages.dashboard.gatedTitle} description={messages.dashboard.gatedDescription} />
          ) : null}

          {pageStatus === "success" && isActivated && cards.length === 0 ? (
            <EmptyState title={messages.dashboard.emptyTitle} description={messages.dashboard.emptyDescription} />
          ) : null}

          {pageStatus === "success" && isActivated && cards.length > 0 ? (
            <DashboardCardGrid cards={cards} messages={messages} />
          ) : null}
        </SectionContainer>
        </MotionPage>
      </PageContainer>
    </ScreenShell>
  );
}
