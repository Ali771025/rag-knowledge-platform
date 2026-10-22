import { LoaderCircle, Mic, MicOff } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import type { VoiceUiState } from "@/features/voice/voice-conversation.types";
import { useI18n } from "@/i18n";
import { dsMotionVariants } from "@/design-system";

interface VoicePulseButtonProps {
  state: VoiceUiState;
  disabled: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function VoicePulseButton({ state, disabled, onStart, onStop }: VoicePulseButtonProps) {
  const shouldReduceMotion = useReducedMotion();
  const { messages } = useI18n();
  const isListening = state === "listening";
  const isProcessing = state === "processing";
  const showListeningPulse = state === "listening" || state === "speaking";

  return (
    <div className="relative flex justify-center py-2">
      <motion.span
        className="absolute inset-0 mx-auto my-auto h-44 w-44 rounded-full border border-cyan-400/35"
        variants={dsMotionVariants.listeningRipple}
        initial="idle"
        animate={shouldReduceMotion ? "idle" : showListeningPulse ? "listening" : "idle"}
        aria-hidden="true"
      />

      <motion.span
        className="absolute inset-0 mx-auto my-auto h-56 w-56 rounded-full border border-violet-400/20"
        variants={dsMotionVariants.listeningRipple}
        initial="idle"
        animate={shouldReduceMotion ? "idle" : showListeningPulse ? "listening" : "idle"}
        aria-hidden="true"
      />

      <motion.button
        type="button"
        onClick={isListening ? onStop : onStart}
        disabled={disabled}
        aria-label={isListening ? messages.voice.stopListening : messages.voice.startListening}
        className={[
          "relative inline-flex h-32 w-32 items-center justify-center rounded-full border border-white/20",
          "bg-gradient-to-br from-cyan-400/40 via-blue-500/40 to-violet-500/45 text-[color:var(--voice-text-main)]",
          "shadow-[0_0_46px_rgba(59,130,246,0.45)] transition",
          "hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--voice-accent-cyan)]",
          "disabled:cursor-not-allowed disabled:opacity-50"
        ].join(" ")}
        variants={dsMotionVariants.micState}
        initial="idle"
        animate={isProcessing ? "processing" : isListening ? "listening" : "idle"}
        whileTap="tap"
      >
        <span className="absolute inset-2 rounded-full border border-white/20 bg-black/20 backdrop-blur-sm" aria-hidden="true" />
        <span className="relative inline-flex">
          {isProcessing ? (
            <LoaderCircle className="h-10 w-10 animate-spin" aria-hidden="true" />
          ) : isListening ? (
            <MicOff className="h-10 w-10" aria-hidden="true" />
          ) : (
            <Mic className="h-10 w-10" aria-hidden="true" />
          )}
        </span>
      </motion.button>
    </div>
  );
}
