import { Activity, LoaderCircle, Mic, Radio, Volume2 } from "lucide-react";
import { useI18n } from "@/i18n";
import { resolveVoiceStatusConfig } from "@/features/voice/voice-conversation.utils";
import type { VoiceUiState } from "@/features/voice/voice-conversation.types";

interface VoiceStatusPillProps {
  state: VoiceUiState;
}

function VoiceStatusIcon({ state }: { state: VoiceUiState }) {
  const config = resolveVoiceStatusConfig(state);
  if (config.icon === "mic") return <Mic className="h-4 w-4" aria-hidden="true" />;
  if (config.icon === "loader") return <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />;
  if (config.icon === "volume") return <Volume2 className="h-4 w-4" aria-hidden="true" />;
  if (config.icon === "alert") return <Activity className="h-4 w-4" aria-hidden="true" />;
  return <Radio className="h-4 w-4" aria-hidden="true" />;
}

export function VoiceStatusPill({ state }: VoiceStatusPillProps) {
  const { messages } = useI18n();
  const config = resolveVoiceStatusConfig(state);

  const labelMap = {
    idle: messages.voice.idleStatus,
    listening: messages.voice.listeningStatus,
    processing: messages.voice.processingStatus,
    speaking: messages.voice.speakingStatus,
    error: messages.voice.errorStatus,
    permission_denied: messages.voice.permissionDeniedStatus
  } as const;

  return (
    <div className="flex justify-center">
      <span className={`inline-flex min-h-9 items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${config.toneClassName}`} role="status" aria-live="polite">
        <span className={state === "listening" ? "agent-orb-pulse" : ""}>
          <VoiceStatusIcon state={state} />
        </span>
        {labelMap[state]}
      </span>
    </div>
  );
}
