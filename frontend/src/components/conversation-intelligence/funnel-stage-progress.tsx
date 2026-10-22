import type { FunnelStage } from "@/types";
import { FUNNEL_STAGES } from "@/types";
import {
  getFunnelProgressPercent,
  getFunnelStageLabel,
  getFunnelStageStep
} from "@/features/conversation-intelligence";

interface FunnelStageProgressProps {
  stage?: FunnelStage | null;
}

// Assumption: stage order follows the shared FUNNEL_STAGES constant from the domain layer.
export function FunnelStageProgress({ stage }: FunnelStageProgressProps) {
  const label = getFunnelStageLabel(stage);
  const currentStep = getFunnelStageStep(stage);
  const totalSteps = FUNNEL_STAGES.length;
  const progressPercent = getFunnelProgressPercent(stage);

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Onboarding progress">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Journey stage</p>
        <p className="text-xs text-muted-foreground">{currentStep === 0 ? "Not started" : `Step ${currentStep}/${totalSteps}`}</p>
      </div>

      <p className="mt-1 text-sm font-semibold text-foreground">{label}</p>

      <div
        className="mt-2 h-1.5 w-full rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressPercent}
        aria-label="Onboarding stage progress"
      >
        <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${progressPercent}%` }} />
      </div>
    </section>
  );
}
