import { motion, useReducedMotion } from "framer-motion";
import { createVoiceWaveBars } from "@/features/voice/voice-conversation.utils";
import type { VoiceUiState } from "@/features/voice/voice-conversation.types";

interface VoiceWaveformProps {
  activeState: VoiceUiState;
  level: number;
}

function clamp(input: number): number {
  return Math.min(Math.max(input, 0), 1);
}

const waveBars = createVoiceWaveBars(18);

export function VoiceWaveform({ activeState, level }: VoiceWaveformProps) {
  const shouldReduceMotion = useReducedMotion();
  const normalized = clamp(level);
  const isActive = activeState === "listening" || activeState === "speaking";

  return (
    <div className="mx-auto grid w-full max-w-[540px] grid-cols-[repeat(18,minmax(0,1fr))] items-end gap-1 px-4" aria-hidden="true">
      {waveBars.map((bar, index) => {
        const height = 8 + Math.round(30 * bar.baseScale + normalized * 30);
        const delay = index * 0.04;
        return (
          <motion.span
            key={bar.id}
            className="rounded-full bg-gradient-to-t from-cyan-400/45 via-blue-400/75 to-violet-400/85"
            style={{ height }}
            animate={
              shouldReduceMotion
                ? undefined
                : {
                    opacity: isActive ? [0.45, 1, 0.45] : 0.35,
                    scaleY: isActive ? [0.7, 1.05 + normalized * 0.35, 0.7] : 0.6
                  }
            }
            transition={
              shouldReduceMotion
                ? undefined
                : {
                    duration: 1.2,
                    repeat: isActive ? Number.POSITIVE_INFINITY : 0,
                    ease: "easeInOut",
                    delay
                  }
            }
          />
        );
      })}
    </div>
  );
}
