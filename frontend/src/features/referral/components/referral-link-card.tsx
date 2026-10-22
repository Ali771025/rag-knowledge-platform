import { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import { Button, CardShell, InputShell, MotionExpandable } from "@/components/ui";
import type { MessagesSchema } from "@/i18n/messages";
import type { ReferralChatThreadSummary, ReferralLinkSummary, ReferralProgressEvent, ReferralTagColor } from "@/services/referral";
import { ReferralLinkActions } from "./referral-link-actions";
import { ReferralLinkChatPanel } from "./referral-link-chat-panel";
import { ReferralLinkProgress } from "./referral-link-progress";
import { ReferralLinkStatusPanel } from "./referral-link-status-panel";

const REFERRAL_COLORS: ReferralTagColor[] = ["blue", "violet", "cyan", "green", "orange", "pink", "gold", "gray"];

function colorClass(color: ReferralTagColor): string {
  const colorMap: Record<ReferralTagColor, string> = {
    blue: "bg-blue-500/20 border-blue-400/50 text-blue-200",
    violet: "bg-violet-500/20 border-violet-400/50 text-violet-200",
    cyan: "bg-cyan-500/20 border-cyan-400/50 text-cyan-200",
    green: "bg-emerald-500/20 border-emerald-400/50 text-emerald-200",
    orange: "bg-orange-500/20 border-orange-400/50 text-orange-200",
    pink: "bg-pink-500/20 border-pink-400/50 text-pink-200",
    gold: "bg-amber-500/20 border-amber-400/50 text-amber-200",
    gray: "bg-slate-500/20 border-slate-400/50 text-slate-200",
  };
  return colorMap[color];
}

function labelForStatus(messages: MessagesSchema, status: ReferralLinkSummary["latestStatus"]): string {
  const map: Record<ReferralLinkSummary["latestStatus"], string> = {
    created: messages.referral.statusCreated,
    invite_opened: messages.referral.statusInviteOpened,
    wallet_connected: messages.referral.statusWalletConnected,
    qora_activated: messages.referral.statusQoraActivated,
    first_microtask_completed: messages.referral.statusFirstMicrotaskCompleted,
    first_achievement_unlocked: messages.referral.statusFirstAchievementUnlocked,
  };
  return map[status];
}

interface ReferralLinkCardProps {
  link: ReferralLinkSummary;
  locale: string;
  messages: MessagesSchema;
  canUseChat: boolean;
  isStatusExpanded: boolean;
  isChatExpanded: boolean;
  statusEvents: ReferralProgressEvent[];
  chatThread: ReferralChatThreadSummary | null;
  chatStatus: "idle" | "loading" | "success" | "error";
  chatSending: boolean;
  onToggleStatus: () => void;
  onToggleChat: () => void;
  onRetryChat: () => void;
  onSendChatMessage: (message: string) => void;
  onCommitLabel: (label: string) => void;
  onCommitColor: (color: ReferralTagColor) => void;
  onCopySuccess: () => void;
  onCopyError: () => void;
  onShareSuccess: () => void;
  onShareUnavailable: () => void;
  onShareError: () => void;
}

export function ReferralLinkCard({
  link,
  locale,
  messages,
  canUseChat,
  isStatusExpanded,
  isChatExpanded,
  statusEvents,
  chatThread,
  chatStatus,
  chatSending,
  onToggleStatus,
  onToggleChat,
  onRetryChat,
  onSendChatMessage,
  onCommitLabel,
  onCommitColor,
  onCopySuccess,
  onCopyError,
  onShareSuccess,
  onShareUnavailable,
  onShareError,
}: ReferralLinkCardProps) {
  const [localLabel, setLocalLabel] = useState(link.label);
  const [editingLabel, setEditingLabel] = useState(false);
  const statusLabel = labelForStatus(messages, link.latestStatus);
  const createdAtLabel = new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(link.createdAt));

  useEffect(() => {
    setLocalLabel(link.label);
  }, [link.label]);

  const statusPanelId = `referral-status-panel-${link.id}`;
  const chatPanelId = `referral-chat-panel-${link.id}`;

  return (
    <CardShell className="p-4">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <span className={["inline-flex items-center rounded-full border px-2 py-0.5 text-[11px]", colorClass(link.color)].join(" ")}>
                {messages.referral.tagColors[link.color]}
              </span>
              {link.isCustomized ? (
                <span className="inline-flex items-center rounded-full border border-emerald-400/40 bg-emerald-500/15 px-2 py-0.5 text-[11px] text-emerald-100">
                  {messages.referral.agentContextAttached}
                </span>
              ) : null}
              <span className="text-xs text-[color:var(--color-text-muted)]">{createdAtLabel}</span>
            </div>
            <div className="flex items-center gap-2">
              <InputShell
                value={localLabel}
                onChange={(event) => {
                  setLocalLabel(event.target.value);
                  setEditingLabel(true);
                }}
                onBlur={() => {
                  const nextLabel = localLabel.trim();
                  if (editingLabel && nextLabel && nextLabel !== link.label) {
                    onCommitLabel(nextLabel);
                  }
                  setEditingLabel(false);
                }}
                className="h-9"
              />
            </div>
            <p className="truncate text-sm text-[color:var(--color-text-main)]">{link.shortUrl}</p>
            <div className="flex flex-wrap gap-1.5">
              {REFERRAL_COLORS.map((item) => (
                <button
                key={`${link.id}-${item}`}
                type="button"
                onClick={() => onCommitColor(item)}
                aria-label={`${messages.referral.selectColorLabel} ${messages.referral.tagColors[item]}`}
                className={[
                  "inline-flex h-7 w-7 items-center justify-center rounded-full border px-2 text-[10px]",
                  colorClass(item),
                    link.color === item ? "ring-1 ring-[color:var(--color-accent-cyan)]" : "",
                  ].join(" ")}
                >
                  <span className="h-2 w-2 rounded-full bg-current opacity-90" aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>
          <ReferralLinkActions
            link={link}
            labels={{ copy: messages.referral.copyButton, share: messages.referral.shareButton }}
            onCopySuccess={onCopySuccess}
            onCopyError={onCopyError}
            onShareSuccess={onShareSuccess}
            onShareUnavailable={onShareUnavailable}
            onShareError={onShareError}
          />
        </div>

        <ReferralLinkProgress progressPercent={link.progressPercent} statusLabel={statusLabel} />

        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onToggleStatus}
            aria-expanded={isStatusExpanded}
            aria-controls={statusPanelId}
          >
            {messages.referral.statusButton}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={onToggleChat}
            disabled={!canUseChat}
            aria-expanded={isChatExpanded}
            aria-controls={chatPanelId}
            title={!canUseChat ? messages.referral.chatDisabledUntilWallet : undefined}
          >
            <MessageCircle className="h-4 w-4" aria-hidden="true" />
            {messages.referral.chatButton}
            {link.unreadMessageCount > 0 ? (
              <span
                className="ml-1 inline-flex min-w-5 items-center justify-center rounded-full bg-[color:var(--color-accent-cyan)] px-1.5 text-[10px] font-semibold text-black"
                aria-label={`${link.unreadMessageCount} ${messages.referral.chatUnreadBadgeLabel}`}
              >
                {link.unreadMessageCount}
              </span>
            ) : null}
          </Button>
          {!canUseChat ? <span className="text-xs text-[color:var(--color-text-muted)]">{messages.referral.chatDisabledUntilWallet}</span> : null}
        </div>

        <MotionExpandable open={isStatusExpanded} className="overflow-hidden">
          <div id={statusPanelId}>
            <ReferralLinkStatusPanel
              locale={locale}
              labels={messages.referral.statusTimeline}
              latestStatus={link.latestStatus}
              events={statusEvents}
            />
          </div>
        </MotionExpandable>
        <MotionExpandable open={isChatExpanded} className="overflow-hidden">
          <div id={chatPanelId}>
            <ReferralLinkChatPanel
              locale={locale}
              thread={chatThread}
              status={chatStatus}
              sending={chatSending}
              labels={{
                panelTitle: messages.referral.chatPanelTitle,
                loading: messages.referral.chatLoadingLabel,
                emptyTitle: messages.referral.chatEmptyTitle,
                emptyDescription: messages.referral.chatEmptyDescription,
                loadError: messages.referral.chatLoadError,
                retry: messages.referral.retry,
                inputPlaceholder: messages.referral.chatInputPlaceholder,
                sendButton: messages.referral.chatSendButton,
                sendAriaLabel: messages.referral.chatSendAriaLabel,
                referrer: messages.referral.chatReferrerLabel,
                invitee: messages.referral.chatInviteeLabel,
                delivery: {
                  sent: messages.referral.chatDeliverySent,
                  delivered: messages.referral.chatDeliveryDelivered,
                  read: messages.referral.chatDeliveryRead,
                },
                showOriginal: messages.referral.chatShowOriginal,
                showTranslation: messages.referral.chatShowTranslation,
                originalTextLabel: messages.referral.chatOriginalTextLabel,
                translatedTextLabel: messages.referral.chatTranslatedTextLabel,
                translationUnavailable: messages.referral.chatTranslationUnavailable,
                translationLoading: messages.referral.chatTranslationLoading,
                translationFailed: messages.referral.chatTranslationFailed,
              }}
              onRetry={onRetryChat}
              onSend={onSendChatMessage}
            />
          </div>
        </MotionExpandable>
      </div>
    </CardShell>
  );
}
