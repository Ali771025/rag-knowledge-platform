import { Bot, Brain, Orbit, Sparkles, Waves } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import type { VoiceUiState } from "@/features/voice/voice-conversation.types";
import { dsMotionVariants } from "@/design-system";

interface VoiceHeroOrbProps {
  state: VoiceUiState;
}

export function VoiceHeroOrb({ state }: VoiceHeroOrbProps) {
  const shouldReduceMotion = useReducedMotion();
  const isActive = state === "listening" || state === "speaking";
  const isProcessing = state === "processing";

  return (
    <div className="relative mx-auto flex h-56 w-56 items-center justify-center sm:h-64 sm:w-64">
      <motion.span
        className="absolute inset-5 rounded-full bg-cyan-500/25 blur-2xl"
        variants={dsMotionVariants.voiceOrb}
        initial="idle"
        animate={shouldReduceMotion ? "idle" : state === "speaking" ? "speaking" : isActive ? "listening" : "idle"}
        aria-hidden="true"
      />
      <motion.span
        className="absolute inset-2 rounded-full border border-violet-400/25"
        variants={dsMotionVariants.voiceProcessingRing}
        initial="idle"
        animate={shouldReduceMotion ? "idle" : isProcessing ? "processing" : "idle"}
        aria-hidden="true"
      />
      <motion.div
        className="relative inline-flex h-44 w-44 items-center justify-center rounded-full border border-[color:var(--voice-border)] bg-gradient-to-br from-slate-950/90 via-blue-950/70 to-black/90 shadow-[0_0_60px_rgba(56,189,248,0.38)] sm:h-48 sm:w-48"
        variants={dsMotionVariants.voiceOrb}
        initial="idle"
        animate={shouldReduceMotion ? "idle" : state === "speaking" ? "speaking" : isActive ? "listening" : "idle"}
      >
        <Bot className="h-16 w-16 text-cyan-200" aria-hidden="true" />
        <span className="absolute -left-1 top-10 rounded-full bg-cyan-500/20 p-1 text-cyan-200">
          <Waves className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="absolute right-2 top-7 rounded-full bg-indigo-500/20 p-1 text-indigo-200">
          <Brain className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="absolute bottom-8 -left-2 rounded-full bg-violet-500/20 p-1 text-violet-200">
          <Orbit className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="absolute -bottom-1 right-8 rounded-full bg-sky-500/20 p-1 text-sky-200">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        </span>
      </motion.div>
    </div>
  );
}
