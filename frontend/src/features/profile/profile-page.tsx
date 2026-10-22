import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Circle, XCircle } from "lucide-react";
import { appRoutes } from "@/app/routes/contracts";
import { LanguageSwitcher } from "@/components/i18n";
import {
  AsyncStatusBadge,
  Button,
  CardShell,
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
import { useToast } from "@/hooks/use-toast";
import { useI18n } from "@/i18n";
import { syncLanguagePreference } from "@/features/language/language-sync";
import { getUserProfile } from "@/core/api";
import { useActivationStore, useAdminAuthStore, useLanguageStore, useProfileStore, useWalletStore } from "@/state";

type ProfileLoadStatus = "loading" | "success" | "error";
type ActivationStatus = "unknown" | "active" | "inactive";

function toActivationLabel(messages: ReturnType<typeof useI18n>["messages"], status: ActivationStatus): string {
  switch (status) {
    case "active":
      return messages.profile.activationActive;
    case "inactive":
      return messages.profile.activationInactive;
    default:
      return messages.profile.activationUnknown;
  }
}

function StepIndicator({
  label,
  completed
}: {
  label: string;
  completed: boolean;
}) {
  return (
    <li className="flex items-center gap-2 text-sm">
      {completed ? (
        <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />
      ) : (
        <Circle className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      )}
      <span className={completed ? "text-foreground" : "text-muted-foreground"}>{label}</span>
    </li>
  );
}

function ProfileSummaryCard({
  fullName,
  email,
  fullNameLabel,
  emailLabel,
  valueUnavailableLabel,
  title
}: {
  fullName: string | null;
  email: string | null;
  fullNameLabel: string;
  emailLabel: string;
  valueUnavailableLabel: string;
  title: string;
}) {
  return (
    <CardShell className="p-4">
      <h2 className={dsTypography.cardTitle}>{title}</h2>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-muted-foreground">{fullNameLabel}</dt>
          <dd className="mt-1 text-sm font-medium text-foreground">{fullName ?? valueUnavailableLabel}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{emailLabel}</dt>
          <dd className="mt-1 text-sm font-medium text-foreground">{email ?? valueUnavailableLabel}</dd>
        </div>
      </dl>
    </CardShell>
  );
}

function ActivationStatusCard({
  title,
  statusLabel,
  status,
  milestoneLabels,
  initialInteractionCompleted,
  registrationCompleted,
  firstTasksReceived
}: {
  title: string;
  statusLabel: string;
  status: ActivationStatus;
  milestoneLabels: {
    initialInteraction: string;
    registration: string;
    firstTasks: string;
  };
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}) {
  return (
    <CardShell className="p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className={dsTypography.cardTitle}>{title}</h2>
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${
            status === "active"
              ? "border-success/35 bg-success/10 text-success"
              : status === "inactive"
                ? "border-error/35 bg-error/10 text-error"
                : "border-border bg-muted/50 text-muted-foreground"
          }`}
        >
          {status === "inactive" ? <XCircle className="h-3.5 w-3.5" aria-hidden="true" /> : null}
          {statusLabel}
        </span>
      </div>
      <ul className="mt-3 space-y-2">
        <StepIndicator label={milestoneLabels.initialInteraction} completed={initialInteractionCompleted} />
        <StepIndicator label={milestoneLabels.registration} completed={registrationCompleted} />
        <StepIndicator label={milestoneLabels.firstTasks} completed={firstTasksReceived} />
      </ul>
    </CardShell>
  );
}

function WalletStatusSection({
  title,
  status,
  address,
  connectLabel,
  disconnectLabel,
  connectedLabel,
  disconnectedLabel,
  onConnect,
  onDisconnect
}: {
  title: string;
  status: "disconnected" | "connecting" | "connected";
  address: string | null;
  connectLabel: string;
  disconnectLabel: string;
  connectedLabel: string;
  disconnectedLabel: string;
  onConnect: () => void;
  onDisconnect: () => void;
}) {
  return (
    <CardShell className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className={dsTypography.cardTitle}>{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {status === "connected" ? connectedLabel : disconnectedLabel}
          </p>
          {status === "connected" && address ? <p className="mt-1 text-sm font-medium text-foreground">{address}</p> : null}
        </div>
        <div className="flex gap-2">
          {status === "connected" ? (
            <Button variant="secondary" size="sm" onClick={onDisconnect}>
              {disconnectLabel}
            </Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={onConnect} disabled={status === "connecting"}>
              {connectLabel}
            </Button>
          )}
        </div>
      </div>
    </CardShell>
  );
}

function PreferencesSection({
  title,
  languageLabel,
  locale,
  onLanguageChange
}: {
  title: string;
  languageLabel: string;
  locale: "en" | "fa" | "ar";
  onLanguageChange: (nextLocale: "en" | "fa" | "ar") => void;
}) {
  return (
    <CardShell className="p-4">
      <h2 className={dsTypography.cardTitle}>{title}</h2>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted-foreground">{languageLabel}</span>
        <LanguageSwitcher value={locale} compact onChange={onLanguageChange} />
      </div>
    </CardShell>
  );
}

export function ProfilePage() {
  const { locale, messages } = useI18n();
  const { success, warning } = useToast();

  const [pageStatus, setPageStatus] = useState<ProfileLoadStatus>("loading");

  const profileStatus = useProfileStore((state) => state.status);
  const profileSummary = useProfileStore((state) => state.summary);
  const setProfileStatus = useProfileStore((state) => state.setStatus);
  const setProfileSummary = useProfileStore((state) => state.setSummary);

  const isAuthenticated = useAdminAuthStore((state) => state.isAuthenticated);
  const clearAuth = useAdminAuthStore((state) => state.clear);

  const selectedLocale = useLanguageStore((state) => state.locale);

  const activationStatus = useActivationStore((state) => state.status);
  const initialInteractionCompleted = useActivationStore((state) => state.initialInteractionCompleted);
  const registrationCompleted = useActivationStore((state) => state.registrationCompleted);
  const firstTasksReceived = useActivationStore((state) => state.firstTasksReceived);
  const walletStatus = useWalletStore((state) => state.status);
  const walletAddress = useWalletStore((state) => state.address);
  const setWalletStatus = useWalletStore((state) => state.setStatus);
  const setWalletAddress = useWalletStore((state) => state.setAddress);
  const disconnectWallet = useWalletStore((state) => state.disconnect);

  const effectiveLocale = useMemo(() => selectedLocale ?? locale, [locale, selectedLocale]);

  const loadProfile = async () => {
    setProfileStatus("loading");
    setPageStatus("loading");
    try {
      if (!isAuthenticated) {
        const fallbackStatus = activationStatus;
        setProfileSummary({
          userId: null,
          fullName: null,
          email: null,
          language: effectiveLocale,
          timezone: null,
          activationStatus: fallbackStatus,
          initialInteractionCompleted,
          registrationCompleted,
          firstTasksReceived,
          isActivated: fallbackStatus === "active",
          eid: null
        });
        setProfileStatus("success");
        setPageStatus("success");
        return;
      }

      const profile = await getUserProfile();

      setProfileSummary({
        userId: profile.user_id ?? null,
        fullName: null,
        email: null,
        language: profile.language ?? effectiveLocale,
        timezone: profile.timezone ?? null,
        activationStatus,
        initialInteractionCompleted,
        registrationCompleted,
        firstTasksReceived,
        isActivated: activationStatus === "active",
        eid: null
      });
      setProfileStatus("success");
      setPageStatus("success");
    } catch {
      setProfileStatus("error");
      setPageStatus("error");
    }
  };

  useEffect(() => {
    void loadProfile();
  }, []);

  const handleLanguageChange = async (nextLocale: "en" | "fa" | "ar") => {
    const result = await syncLanguagePreference({
      desiredLocale: nextLocale,
      strategy: "prefer-local"
    });

    if (result.source !== "local") {
      warning(messages.language.syncFailed);
      return;
    }

    setProfileSummary(
      profileSummary
        ? {
            ...profileSummary,
            language: nextLocale
          }
        : profileSummary
    );
    success(messages.profile.languageSaved);
  };

  const handleWalletConnect = () => {
    if (walletStatus === "connected") return;
    setWalletStatus("connecting");
    window.setTimeout(() => {
      setWalletAddress("0xA11...F9C");
      setWalletStatus("connected");
      success(messages.profile.walletConnected);
    }, 320);
  };

  const handleWalletDisconnect = () => {
    disconnectWallet();
    success(messages.profile.walletDisconnected);
  };

  const handleLogout = () => {
    clearAuth();
    disconnectWallet();
    success(messages.profile.loggedOut);
    window.location.assign(appRoutes.language);
  };

  return (
    <ScreenShell>
      <PageContainer className="py-8 sm:py-10">
        <MotionPage>
        <SectionContainer className="mx-auto w-full max-w-4xl space-y-4">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className={dsTypography.pageTitle}>{messages.profile.pageTitle}</h1>
              <p className="mt-1 text-sm text-muted-foreground">{messages.profile.pageSubtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              <AsyncStatusBadge status={profileStatus === "idle" ? "idle" : profileStatus} />
              <Link to={appRoutes.agent}>
                <Button variant="secondary" size="md">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  {messages.profile.backToChat}
                </Button>
              </Link>
            </div>
          </header>

          {pageStatus === "loading" ? (
            <CardShell className="p-4">
              <div role="status" aria-live="polite" aria-label={messages.profile.loadingLabel}>
                <LoadingSkeleton lines={6} />
              </div>
            </CardShell>
          ) : null}

          {pageStatus === "error" ? (
            <ErrorPanel
              title={messages.profile.errorTitle}
              message={messages.profile.errorMessage}
              retryLabel={messages.profile.retry}
              onRetry={() => {
                void loadProfile();
              }}
            />
          ) : null}

          {pageStatus === "success" ? (
            <MotionList className="space-y-4">
              <MotionListItem>
                <ProfileSummaryCard
                  title={messages.profile.summaryTitle}
                  fullNameLabel={messages.profile.fullNameLabel}
                  emailLabel={messages.profile.emailLabel}
                  valueUnavailableLabel={messages.profile.valueUnavailable}
                  fullName={profileSummary?.fullName ?? null}
                  email={profileSummary?.email ?? null}
                />
              </MotionListItem>

              <MotionListItem>
                <ActivationStatusCard
                  title={messages.profile.activationTitle}
                  statusLabel={toActivationLabel(messages, profileSummary?.activationStatus ?? activationStatus)}
                  status={profileSummary?.activationStatus ?? activationStatus}
                  milestoneLabels={{
                    initialInteraction: messages.profile.initialInteractionLabel,
                    registration: messages.profile.registrationLabel,
                    firstTasks: messages.profile.firstTasksLabel
                  }}
                  initialInteractionCompleted={profileSummary?.initialInteractionCompleted ?? initialInteractionCompleted}
                  registrationCompleted={profileSummary?.registrationCompleted ?? registrationCompleted}
                  firstTasksReceived={profileSummary?.firstTasksReceived ?? firstTasksReceived}
                />
              </MotionListItem>

              <MotionListItem>
                <PreferencesSection
                  title={messages.profile.preferencesTitle}
                  languageLabel={messages.profile.languageLabel}
                  locale={effectiveLocale}
                  onLanguageChange={handleLanguageChange}
                />
              </MotionListItem>

              <MotionListItem>
                <WalletStatusSection
                  title={messages.profile.walletTitle}
                  status={walletStatus}
                  address={walletAddress}
                  connectLabel={messages.profile.connectWallet}
                  disconnectLabel={messages.profile.disconnectWallet}
                  connectedLabel={messages.profile.walletConnectedStatus}
                  disconnectedLabel={messages.profile.walletDisconnectedStatus}
                  onConnect={handleWalletConnect}
                  onDisconnect={handleWalletDisconnect}
                />
              </MotionListItem>

              {isAuthenticated ? (
                <MotionListItem>
                  <CardShell className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <h2 className={dsTypography.cardTitle}>{messages.profile.sessionTitle}</h2>
                        <p className="mt-1 text-sm text-muted-foreground">{messages.profile.sessionDescription}</p>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleLogout}
                      >
                        {messages.profile.logoutAction}
                      </Button>
                    </div>
                  </CardShell>
                </MotionListItem>
              ) : null}
            </MotionList>
          ) : null}
        </SectionContainer>
        </MotionPage>
      </PageContainer>
    </ScreenShell>
  );
}
