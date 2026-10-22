import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button, LoadingDots } from "@/components/ui";
import type { ReferralChatMessage, ReferralChatThreadSummary } from "@/services/referral";

type ReferralChatStatus = "idle" | "loading" | "success" | "error";

interface ReferralLinkChatLabels {
  panelTitle: string;
  loading: string;
  emptyTitle: string;
  emptyDescription: string;
  loadError: string;
  retry: string;
  inputPlaceholder: string;
  sendButton: string;
  sendAriaLabel: string;
  referrer: string;
  invitee: string;
  delivery: {
    sent: string;
    delivered: string;
    read: string;
  };
  showOriginal: string;
  showTranslation: string;
  originalTextLabel: string;
  translatedTextLabel: string;
  translationUnavailable: string;
  translationLoading: string;
  translationFailed: string;
}

interface ReferralLinkChatPanelProps {
  locale: string;
  thread: ReferralChatThreadSummary | null;
  status: ReferralChatStatus;
  sending: boolean;
  labels: ReferralLinkChatLabels;
  onRetry: () => void;
  onSend: (message: string) => void;
}

function isRtlText(localeOrText: string): boolean {
  const normalized = localeOrText.trim().toLowerCase();
  if (normalized.startsWith("fa") || normalized.startsWith("ar")) return true;
  return /[\u0600-\u06FF]/.test(localeOrText);
}

function normalizeLocale(locale: string): string {
  return locale.trim().toLowerCase().replace("_", "-").split("-", 1)[0] || "en";
}

function senderLabel(message: ReferralChatMessage, labels: ReferralLinkChatLabels): string {
  return message.senderRole === "referrer" ? labels.referrer : labels.invitee;
}

function deliveryLabel(message: ReferralChatMessage, labels: ReferralLinkChatLabels): string {
  return labels.delivery[message.deliveryStatus];
}

function ReferralMessageBubble({
  message,
  viewerRole,
  locale,
  labels,
  showOriginal,
  onToggleOriginal,
}: {
  message: ReferralChatMessage;
  viewerRole: "referrer" | "invitee";
  locale: string;
  labels: ReferralLinkChatLabels;
  showOriginal: boolean;
  onToggleOriginal: () => void;
}) {
  const isOwn = message.senderRole === viewerRole;
  const translatedText = message.translatedTextForViewer?.trim() || null;
  const hasTranslation = Boolean(translatedText && translatedText !== message.originalText);
  const primaryText = hasTranslation && !showOriginal ? translatedText : message.originalText;
  const textDirection = isRtlText(primaryText || message.originalLocale) ? "rtl" : "ltr";
  const translationMissing =
    !hasTranslation && message.senderRole !== viewerRole && normalizeLocale(message.originalLocale) !== normalizeLocale(locale);
  const timestamp = new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(message.createdAt));
  const contentLabel = hasTranslation && !showOriginal ? labels.translatedTextLabel : labels.originalTextLabel;

  return (
    <li className={["flex", isOwn ? "justify-end" : "justify-start"].join(" ")}>
      <article
        className={[
          "max-w-[86%] rounded-2xl px-3 py-2 shadow-sm outline-none ring-offset-2 ring-offset-transparent focus-within:ring-2 focus-within:ring-[color:var(--color-accent-cyan)] sm:max-w-[72%]",
          isOwn
            ? "rounded-br-md bg-[color:var(--color-accent-violet)] text-white"
            : "rounded-bl-md border border-white/10 bg-black/35 text-[color:var(--color-text-main)]",
        ].join(" ")}
      >
        <div className={["mb-1 flex items-center gap-2 text-[10px] opacity-75", isOwn ? "justify-end" : "justify-start"].join(" ")}>
          <span>{senderLabel(message, labels)}</span>
          <span aria-hidden="true">·</span>
          <time dateTime={message.createdAt}>{timestamp}</time>
        </div>
        <p className="mb-1 text-[10px] uppercase tracking-wide opacity-60">{contentLabel}</p>
        <p dir={textDirection} className="whitespace-pre-wrap break-words text-sm leading-6">
          {primaryText}
        </p>
        {hasTranslation ? (
          <button
            type="button"
            onClick={onToggleOriginal}
            className="mt-2 text-[11px] font-medium underline decoration-white/40 underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent-cyan)]"
          >
            {showOriginal ? labels.showTranslation : labels.showOriginal}
          </button>
        ) : null}
        {translationMissing ? (
          <p className="mt-2 text-[11px] opacity-65">
            {labels.translationFailed}: {labels.translationUnavailable}
          </p>
        ) : null}
        {isOwn ? (
          <p className="mt-1 text-right text-[10px] opacity-70">{deliveryLabel(message, labels)}</p>
        ) : null}
      </article>
    </li>
  );
}

export function ReferralLinkChatPanel({
  locale,
  thread,
  status,
  sending,
  labels,
  onRetry,
  onSend,
}: ReferralLinkChatPanelProps) {
  const [draft, setDraft] = useState("");
  const [originalOpenByMessageId, setOriginalOpenByMessageId] = useState<Record<string, boolean>>({});
  const listEndRef = useRef<HTMLDivElement | null>(null);
  const messages = useMemo(() => thread?.messages ?? [], [thread?.messages]);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages.length, status]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;
    onSend(message);
    setDraft("");
  };

  return (
    <section
      className="overflow-hidden rounded-xl border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-soft)]"
      aria-label={labels.panelTitle}
    >
      <div className="border-b border-white/10 px-3 py-2">
        <h3 className="text-xs font-semibold text-[color:var(--color-text-main)]">{labels.panelTitle}</h3>
      </div>
      <div className="max-h-80 min-h-40 overflow-y-auto px-3 py-3" aria-live="polite" aria-busy={status === "loading"}>
        {status === "loading" ? (
          <div
            className="flex min-h-28 items-center justify-center text-xs text-[color:var(--color-text-muted)]"
            role="status"
            aria-label={`${labels.loading}. ${labels.translationLoading}`}
          >
            <LoadingDots />
          </div>
        ) : null}

        {status === "error" ? (
          <div className="flex min-h-28 flex-col items-center justify-center gap-3 text-center">
            <p className="text-sm text-[color:var(--color-text-main)]">{labels.loadError}</p>
            <Button variant="secondary" size="sm" onClick={onRetry} aria-label={labels.retry}>
              {labels.retry}
            </Button>
          </div>
        ) : null}

        {status === "success" && messages.length === 0 ? (
          <div className="flex min-h-28 flex-col justify-center text-center">
            <p className="text-sm font-semibold text-[color:var(--color-text-main)]">{labels.emptyTitle}</p>
            <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">{labels.emptyDescription}</p>
          </div>
        ) : null}

        {status === "success" && messages.length > 0 ? (
          <ul className="space-y-2">
            {messages.map((message) => (
              <ReferralMessageBubble
                key={message.id}
                message={message}
                viewerRole={thread?.currentUserRole ?? "referrer"}
                locale={locale}
                labels={labels}
                showOriginal={Boolean(originalOpenByMessageId[message.id])}
                onToggleOriginal={() =>
                  setOriginalOpenByMessageId((state) => ({
                    ...state,
                    [message.id]: !Boolean(state[message.id]),
                  }))
                }
              />
            ))}
          </ul>
        ) : null}
        <div ref={listEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-white/10 bg-black/20 p-2">
        <label className="sr-only" htmlFor={`referral-chat-input-${thread?.referralLinkId ?? "pending"}`}>
          {labels.inputPlaceholder}
        </label>
        <textarea
          id={`referral-chat-input-${thread?.referralLinkId ?? "pending"}`}
          value={draft}
          rows={1}
          dir={isRtlText(locale) ? "rtl" : "ltr"}
          aria-invalid={false}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={labels.inputPlaceholder}
          className="min-h-10 flex-1 resize-none rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-[color:var(--color-text-main)] outline-none transition focus:border-[color:var(--color-accent-cyan)] focus:ring-2 focus:ring-[color:var(--color-accent-cyan)]/30"
          disabled={status !== "success" || sending}
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={status !== "success" || sending || !draft.trim()}
          aria-label={labels.sendAriaLabel}
        >
          <Send className="h-4 w-4" aria-hidden="true" />
          {labels.sendButton}
        </Button>
      </form>
    </section>
  );
}

export const ReferralLinkChatPanelPlaceholder = ReferralLinkChatPanel;
