import { ArrowLeft, MessageSquareText, X } from "lucide-react";
import { GradientButton, IconButton } from "@/components/ui";
import { useI18n } from "@/i18n";

interface VoiceBottomActionsProps {
  onReturn: () => void;
  onSwitchToTyping: () => void;
  onClose: () => void;
}

export function VoiceBottomActions({ onReturn, onSwitchToTyping, onClose }: VoiceBottomActionsProps) {
  const { messages, direction } = useI18n();
  const backIconClass = ["h-4 w-4", direction === "rtl" ? "rotate-180" : ""].join(" ");

  return (
    <div className="relative mx-auto flex w-full max-w-3xl flex-wrap items-center justify-center gap-2 px-1 pb-3 sm:gap-3">
      <button
        type="button"
        onClick={onReturn}
        className="inline-flex min-h-11 items-center gap-2 rounded-2xl border border-white/15 bg-[color:var(--voice-surface-soft)] px-4 py-2 text-sm text-[color:var(--voice-text-main)] transition hover:border-[color:var(--voice-border)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--voice-accent-cyan)]"
      >
        <ArrowLeft className={backIconClass} aria-hidden="true" />
        {messages.voice.returnToChat}
      </button>

      <GradientButton
        size="md"
        onClick={onSwitchToTyping}
        leadingIcon={<MessageSquareText className="h-4 w-4" aria-hidden="true" />}
      >
        {messages.voice.switchToTyping}
      </GradientButton>

      <div className="fixed bottom-6 end-5 z-30 sm:end-8">
        <IconButton variant="secondary" className="h-12 w-12 rounded-full border border-white/20 bg-black/35 backdrop-blur-xl" onClick={onClose} aria-label={messages.voice.close}>
          <X className="h-5 w-5" aria-hidden="true" />
        </IconButton>
      </div>

      <span className="sr-only">{messages.voice.liveTranscriptPlaceholder}</span>
    </div>
  );
}
