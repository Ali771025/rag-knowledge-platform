import { Skeleton } from "@/components/ui";
import { dsTypography } from "@/design-system";
import { getOnboardingTimelineStatusLabel, type OnboardingTimelineStepViewModel } from "@/features/onboarding";

interface OnboardingTimelineProps {
  steps: OnboardingTimelineStepViewModel[];
  currentStep?: OnboardingTimelineStepViewModel | null;
  completionPercent?: number;
  isLoading?: boolean;
}

const TIMELINE_MARKER_CLASS = {
  complete: "border-success bg-success/20 text-success",
  current: "border-primary bg-primary/15 text-primary",
  blocked: "border-warning bg-warning/15 text-warning",
  upcoming: "border-border bg-muted text-muted-foreground",
  not_started: "border-border bg-muted text-muted-foreground"
} as const;

function TimelineSkeleton() {
  return (
    <div className="space-y-2" aria-hidden="true">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
    </div>
  );
}

export function OnboardingTimeline({
  steps,
  currentStep = null,
  completionPercent = 0,
  isLoading = false
}: OnboardingTimelineProps) {
  if (isLoading && steps.length === 0) {
    return <TimelineSkeleton />;
  }

  if (steps.length === 0) {
    return <p className="text-sm text-muted-foreground">The workflow timeline will appear as the session progresses.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className={dsTypography.secondary}>
          {currentStep ? `Current: ${currentStep.title}` : "Timeline"}
        </p>
        <p className="text-xs text-muted-foreground">{completionPercent}%</p>
      </div>

      <ol className="space-y-2" aria-label="Onboarding timeline">
        {steps.map((step) => (
          <li
            key={step.id}
            className={`rounded-xl border px-3 py-2 ${step.isCurrent ? "border-primary/40 bg-primary/5" : "border-border/70 bg-background"}`}
            aria-current={step.isCurrent ? "step" : undefined}
          >
            <div className="flex items-start gap-3">
              <span
                className={`mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full border text-[10px] font-semibold ${TIMELINE_MARKER_CLASS[step.status]}`}
                aria-hidden="true"
              >
                {step.isComplete ? "✓" : step.isBlocked ? "!" : step.order}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-medium text-foreground">{step.title}</p>
                  <span className="shrink-0 text-[11px] uppercase tracking-wide text-muted-foreground">
                    {getOnboardingTimelineStatusLabel(step.status)}
                  </span>
                </div>
                {step.description ? <p className="mt-1 text-xs text-muted-foreground">{step.description}</p> : null}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
