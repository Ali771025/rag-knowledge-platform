import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { appRoutes } from "@/app/routes/contracts";
import {
  AsyncStatusBadge,
  Button,
  CardShell,
  EmptyState,
  ErrorPanel,
  LoadingSkeleton,
} from "@/components/ui";
import { dsTypography } from "@/design-system";
import { useToast } from "@/hooks/use-toast";
import { useI18n } from "@/i18n";
import { referralService } from "@/services/referral";
import type { ReferralLinkSummary, ReferralPersonalizationProfile, ReferralTagColor } from "@/services/referral";
import { useReferralStore } from "@/state";
import { ReferralCreatePanel } from "./components/referral-create-panel";
import { ReferralDashboardPage } from "./components/referral-dashboard-page";
import { ReferralDraftCard } from "./components/referral-draft-card";
import { ReferralLinkList } from "./components/referral-link-list";
import { ReferralPersonalizationWizard } from "./components/referral-personalization-wizard";
import { ReferralStatsStrip } from "./components/referral-stats-strip";

type ReferralLoadStatus = "loading" | "success" | "error";
type ReferralChatLoadStatus = "idle" | "loading" | "success" | "error";

function buildPreviewShortUrl(label: string): string {
  const fallbackCode = "REF-DRAFT";
  const normalized = label.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "-").slice(0, 10);
  const code = normalized || fallbackCode;
  return `https://example.invalid/register?invite=${code}`;
}

export function ReferralPage() {
  const { locale, messages } = useI18n();
  const { success, warning, error } = useToast();

  const status = useReferralStore((state) => state.status);
  const stats = useReferralStore((state) => state.stats);
  const links = useReferralStore((state) => state.links);
  const draft = useReferralStore((state) => state.draft);
  const progressEventsByLinkId = useReferralStore((state) => state.progressEventsByLinkId);
  const chatThreadByLinkId = useReferralStore((state) => state.chatThreadByLinkId);
  const expandedStatusByLinkId = useReferralStore((state) => state.expandedStatusByLinkId);
  const setStatus = useReferralStore((state) => state.setStatus);
  const setStats = useReferralStore((state) => state.setStats);
  const setLinks = useReferralStore((state) => state.setLinks);
  const prependLink = useReferralStore((state) => state.prependLink);
  const updateLink = useReferralStore((state) => state.updateLink);
  const setProgressEvents = useReferralStore((state) => state.setProgressEvents);
  const setChatThread = useReferralStore((state) => state.setChatThread);
  const setDraft = useReferralStore((state) => state.setDraft);
  const patchDraft = useReferralStore((state) => state.patchDraft);
  const setStatusPanelExpanded = useReferralStore((state) => state.setStatusPanelExpanded);

  const [pageStatus, setPageStatus] = useState<ReferralLoadStatus>("loading");
  const [errorState, setErrorState] = useState(false);
  const [expandedChatByLinkId, setExpandedChatByLinkId] = useState<Record<string, boolean>>({});
  const [chatStatusByLinkId, setChatStatusByLinkId] = useState<Record<string, ReferralChatLoadStatus>>({});
  const [chatSendingByLinkId, setChatSendingByLinkId] = useState<Record<string, boolean>>({});
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardSubmitting, setWizardSubmitting] = useState(false);

  const loadReferral = async () => {
    setPageStatus("loading");
    setStatus("loading");
    setErrorState(false);
    try {
      const [statsSnapshot, linksSnapshot] = await Promise.all([referralService.getDashboardStats(), referralService.listLinks()]);
      setStats(statsSnapshot);
      setLinks(linksSnapshot);
      setStatus("success");
      setPageStatus("success");
    } catch {
      setStatus("error");
      setPageStatus("error");
      setErrorState(true);
    }
  };

  useEffect(() => {
    void loadReferral();
  }, []);

  const effectiveStats = useMemo(() => {
    if (stats) return stats;
    return {
      totalInvites: 0,
      activatedQora: 0,
      firstMicroTask: 0,
      firstAchievement: 0,
    };
  }, [stats]);

  const handleCreateDraft = () => {
    if (draft) return;
    setDraft({
      label: messages.referral.defaultDraftLabel,
      color: "blue",
    });
  };

  const handleCreateRegularLink = async () => {
    if (!draft) return;
    const nextLabel = draft.label.trim();
    if (!nextLabel) return;

    try {
      const created = await referralService.createLink({
        label: nextLabel,
        color: draft.color,
      });
      prependLink(created);
      setDraft(null);
      const nextStats = await referralService.getDashboardStats();
      setStats(nextStats);
      success(messages.referral.createLinkSuccessTitle);
    } catch {
      error(messages.referral.createLinkErrorTitle);
    }
  };

  const handleCreateCustomizedLink = async (profile: ReferralPersonalizationProfile) => {
    if (!draft) return;
    const nextLabel = draft.label.trim();
    if (!nextLabel) return;
    setWizardSubmitting(true);
    try {
      const created = await referralService.createCustomizedLink({
        label: nextLabel,
        color: draft.color,
        personalizationProfile: profile,
      });
      prependLink(created);
      setDraft(null);
      setWizardOpen(false);
      const nextStats = await referralService.getDashboardStats();
      setStats(nextStats);
      success(messages.referral.createCustomizedLinkSuccessTitle);
    } catch {
      error(messages.referral.createCustomizedLinkErrorTitle);
    } finally {
      setWizardSubmitting(false);
    }
  };

  const handleUpdateLinkLabel = async (linkId: string, label: string) => {
    try {
      const updated = await referralService.updateLink(linkId, { label });
      updateLink(linkId, {
        label: updated.label,
      });
      success(messages.referral.linkUpdatedTitle);
    } catch {
      error(messages.referral.linkUpdateErrorTitle);
    }
  };

  const handleUpdateLinkColor = async (linkId: string, color: ReferralTagColor) => {
    try {
      const updated = await referralService.updateLink(linkId, { color });
      updateLink(linkId, {
        color: updated.color,
      });
      success(messages.referral.linkUpdatedTitle);
    } catch {
      error(messages.referral.linkUpdateErrorTitle);
    }
  };

  const handleToggleStatus = async (linkId: string) => {
    const nextExpanded = !Boolean(expandedStatusByLinkId[linkId]);
    setStatusPanelExpanded(linkId, nextExpanded);
    if (!nextExpanded) return;
    try {
      const events = await referralService.getProgressEvents(linkId);
      setProgressEvents(linkId, events);
    } catch {
      warning(messages.referral.statusLoadWarningTitle);
    }
  };

  const canUseChat = useCallback((link: ReferralLinkSummary) => {
    if (link.chatEnabled) return true;
    return ["wallet_connected", "qora_activated", "first_microtask_completed", "first_achievement_unlocked"].includes(link.latestStatus);
  }, []);

  const loadReferralChat = useCallback(
    async (linkId: string, options?: { silent?: boolean; markRead?: boolean }) => {
      if (!options?.silent) {
        setChatStatusByLinkId((state) => ({ ...state, [linkId]: "loading" }));
      }
      try {
        const thread = await referralService.getChatThread(linkId, locale);
        setChatThread(linkId, thread);
        updateLink(linkId, { unreadMessageCount: thread.unreadMessageCount });

        if ((options?.markRead ?? true) && thread.unreadMessageCount > 0) {
          const readThread = await referralService.markChatThreadRead(linkId, locale);
          setChatThread(linkId, readThread);
          updateLink(linkId, { unreadMessageCount: readThread.unreadMessageCount });
        }

        setChatStatusByLinkId((state) => ({ ...state, [linkId]: "success" }));
      } catch {
        setChatStatusByLinkId((state) => ({ ...state, [linkId]: "error" }));
      }
    },
    [locale, setChatThread, updateLink]
  );

  const handleToggleChat = (linkId: string) => {
    const link = links.find((item) => item.id === linkId);
    if (!link || !canUseChat(link)) return;
    const nextExpanded = !Boolean(expandedChatByLinkId[linkId]);
    setExpandedChatByLinkId((state) => ({
      ...state,
      [linkId]: nextExpanded,
    }));
    if (nextExpanded) {
      void loadReferralChat(linkId);
    }
  };

  const handleSendChatMessage = async (linkId: string, message: string) => {
    setChatSendingByLinkId((state) => ({ ...state, [linkId]: true }));
    try {
      await referralService.sendChatMessage(linkId, {
        message,
        originalLocale: locale,
        sourceLanguage: locale,
      });
      await loadReferralChat(linkId, { silent: true, markRead: true });
    } catch {
      error(messages.referral.chatSendErrorTitle);
    } finally {
      setChatSendingByLinkId((state) => ({ ...state, [linkId]: false }));
    }
  };

  const expandedEnabledChatLinkIds = useMemo(
    () => links.filter((link) => expandedChatByLinkId[link.id] && canUseChat(link)).map((link) => link.id),
    [canUseChat, expandedChatByLinkId, links]
  );

  useEffect(() => {
    if (expandedEnabledChatLinkIds.length === 0) return;
    const intervalId = window.setInterval(() => {
      expandedEnabledChatLinkIds.forEach((linkId) => {
        void loadReferralChat(linkId, { silent: true, markRead: true });
      });
    }, 10_000);
    return () => window.clearInterval(intervalId);
  }, [expandedEnabledChatLinkIds, loadReferralChat]);

  return (
    <ReferralDashboardPage>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className={dsTypography.pageTitle}>{messages.referral.pageTitle}</h1>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">{messages.referral.pageSubtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <AsyncStatusBadge status={status === "idle" ? "idle" : status} />
          <Link to={appRoutes.agent}>
            <Button variant="secondary" size="md">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              {messages.referral.backToChat}
            </Button>
          </Link>
        </div>
      </header>

      {pageStatus === "loading" ? (
        <CardShell className="p-4">
          <div role="status" aria-live="polite" aria-label={messages.referral.loadingLabel}>
            <LoadingSkeleton lines={8} />
          </div>
        </CardShell>
      ) : null}

      {pageStatus === "error" || errorState ? (
        <ErrorPanel
          title={messages.referral.errorTitle}
          message={messages.referral.errorMessage}
          retryLabel={messages.referral.retry}
          onRetry={() => {
            void loadReferral();
          }}
        />
      ) : null}

      {pageStatus === "success" ? (
        <>
          <ReferralStatsStrip
            locale={locale}
            stats={effectiveStats}
            labels={{
              totalInvites: messages.referral.totalInvitesLabel,
              activatedQora: messages.referral.activatedQoraLabel,
              firstMicroTask: messages.referral.firstMicroTaskLabel,
              firstAchievement: messages.referral.firstAchievementLabel,
            }}
          />

          <ReferralCreatePanel
            title={messages.referral.createPanelTitle}
            subtitle={messages.referral.createPanelSubtitle}
            createLabel={messages.referral.addLinkButton}
            onCreateDraft={handleCreateDraft}
          />

          {draft ? (
            <ReferralDraftCard
              label={draft.label}
              color={draft.color}
              shortUrlPreview={buildPreviewShortUrl(draft.label)}
              labels={{
                draftTitle: messages.referral.draftTitle,
                draftLabel: messages.referral.draftLabel,
                draftUrlPreview: messages.referral.draftUrlPreview,
                selectColor: messages.referral.selectColorLabel,
                done: messages.referral.doneButton,
                customize: messages.referral.customizeButton,
                tagColors: messages.referral.tagColors,
              }}
              onChangeLabel={(next) => patchDraft({ label: next })}
              onSelectColor={(next) => patchDraft({ color: next })}
              onDone={() => {
                void handleCreateRegularLink();
              }}
              onCustomize={() => setWizardOpen(true)}
            />
          ) : null}

          {links.length === 0 ? (
            <EmptyState title={messages.referral.noDataTitle} description={messages.referral.noDataDescription} />
          ) : (
            <ReferralLinkList
              links={links}
              locale={locale}
              messages={messages}
              expandedStatusByLinkId={expandedStatusByLinkId}
              expandedChatByLinkId={expandedChatByLinkId}
              statusEventsByLinkId={progressEventsByLinkId}
              chatThreadByLinkId={chatThreadByLinkId}
              chatStatusByLinkId={chatStatusByLinkId}
              chatSendingByLinkId={chatSendingByLinkId}
              canUseChat={canUseChat}
              onToggleStatus={(linkId) => {
                void handleToggleStatus(linkId);
              }}
              onToggleChat={handleToggleChat}
              onRetryChat={(linkId) => {
                void loadReferralChat(linkId);
              }}
              onSendChatMessage={(linkId, message) => {
                void handleSendChatMessage(linkId, message);
              }}
              onCommitLabel={(linkId, label) => {
                void handleUpdateLinkLabel(linkId, label);
              }}
              onCommitColor={(linkId, color) => {
                void handleUpdateLinkColor(linkId, color);
              }}
              onCopySuccess={() => success(messages.referral.copySuccessTitle)}
              onCopyError={() => error(messages.referral.copyErrorTitle)}
              onShareSuccess={() => success(messages.referral.shareSuccessTitle)}
              onShareUnavailable={() => warning(messages.referral.shareUnavailableTitle)}
              onShareError={() => error(messages.referral.shareErrorTitle)}
            />
          )}

          {draft ? (
            <ReferralPersonalizationWizard
              open={wizardOpen}
              labels={messages.referral.personalizationWizard}
              draftLabel={draft.label}
              draftColorLabel={messages.referral.tagColors[draft.color]}
              initialValue={null}
              submitting={wizardSubmitting}
              onClose={() => setWizardOpen(false)}
              onSubmit={(profile) => {
                void handleCreateCustomizedLink(profile);
              }}
            />
          ) : null}
        </>
      ) : null}
    </ReferralDashboardPage>
  );
}
