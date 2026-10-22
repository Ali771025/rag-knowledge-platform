import type { VoiceStatusConfig, VoiceUiState, VoiceWaveBar } from "./voice-conversation.types";

export function resolveVoiceStatusConfig(state: VoiceUiState): VoiceStatusConfig {
  if (state === "listening") {
    return {
      icon: "mic",
      toneClassName: "border-cyan-400/35 bg-cyan-500/15 text-cyan-200"
    };
  }
  if (state === "processing") {
    return {
      icon: "loader",
      toneClassName: "border-amber-400/35 bg-amber-500/15 text-amber-200"
    };
  }
  if (state === "speaking") {
    return {
      icon: "volume",
      toneClassName: "border-violet-400/35 bg-violet-500/15 text-violet-200"
    };
  }
  if (state === "error" || state === "permission_denied") {
    return {
      icon: "alert",
      toneClassName: "border-rose-400/35 bg-rose-500/15 text-rose-200"
    };
  }
  return {
    icon: "radio",
    toneClassName: "border-emerald-400/35 bg-emerald-500/15 text-emerald-200"
  };
}

export function createVoiceWaveBars(count: number): VoiceWaveBar[] {
  return Array.from({ length: count }, (_, index) => {
    const baseScale = 0.32 + (index % 5) * 0.12;
    return {
      id: index,
      baseScale: Number(baseScale.toFixed(2))
    };
  });
}

export function getVoiceTranscriptDirection(text: string): "rtl" | "ltr" {
  const rtlPattern = /[\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC]/;
  return rtlPattern.test(text) ? "rtl" : "ltr";
}
