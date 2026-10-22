export type VoiceUiState = "idle" | "listening" | "processing" | "speaking" | "error" | "permission_denied";

export type VoiceStatusIconKey = "radio" | "mic" | "loader" | "volume" | "alert";

export interface VoiceStatusConfig {
  icon: VoiceStatusIconKey;
  toneClassName: string;
}

export interface VoiceWaveBar {
  id: number;
  baseScale: number;
}
