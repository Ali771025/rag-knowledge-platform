import { MessageSquareText } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui";
import { useI18n } from "@/i18n";
import { getVoiceTranscriptDirection } from "@/features/voice/voice-conversation.utils";
import { dsMotionVariants } from "@/design-system";

interface VoiceTranscriptPanelProps {
  partialTranscript: string;
  finalTranscript: string;
}

function mergeTranscript(finalTranscript: string, partialTranscript: string): string {
  const finalText = finalTranscript.trim();
  const partialText = partialTranscript.trim();
  if (!finalText && !partialText) return "";
  return [finalText, partialText].filter(Boolean).join("\n").trim();
}

export function VoiceTranscriptPanel({ partialTranscript, finalTranscript }: VoiceTranscriptPanelProps) {
  const { messages } = useI18n();
  const transcript = mergeTranscript(finalTranscript, partialTranscript);
  const hasTranscript = transcript.length > 0;
  const transcriptDir = getVoiceTranscriptDirection(transcript || messages.voice.transcriptEmptyState);

  return (
    <GlassCard className="mx-auto w-full max-w-2xl p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--voice-text-main)] sm:text-base">
          <MessageSquareText className="h-4 w-4" aria-hidden="true" />
          {messages.voice.liveTranscriptTitle}
        </h2>
      </div>
      <section
        className="max-h-48 min-h-28 overflow-auto rounded-2xl border border-white/10 bg-black/20 p-3 sm:max-h-56"
        aria-live="polite"
        aria-atomic="false"
      >
        {hasTranscript ? (
          <motion.p
            key={transcript}
            dir={transcriptDir}
            className="whitespace-pre-wrap break-words text-sm leading-7 text-[color:var(--voice-text-main)]"
            variants={dsMotionVariants.streamingReveal}
            initial="hidden"
            animate="visible"
          >
            {transcript}
          </motion.p>
        ) : (
          <p dir={transcriptDir} className="text-sm text-[color:var(--voice-text-muted)]">
            {messages.voice.transcriptEmptyState}
          </p>
        )}
      </section>
    </GlassCard>
  );
}
