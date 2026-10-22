import { getOnboardingSessionResumeStatusLabel, type OnboardingSessionResumeStateViewModel } from "@/features/onboarding";

interface SessionResumeBannerProps {
  sessionResume: OnboardingSessionResumeStateViewModel;
  onResume?: (sessionResume: OnboardingSessionResumeStateViewModel) => void;
}

export function SessionResumeBanner({ sessionResume, onResume }: SessionResumeBannerProps) {
  if (!sessionResume.isAvailable) {
    return <p className="text-sm text-muted-foreground">{sessionResume.message}</p>;
  }

  return (
    <div className="rounded-xl border border-border/70 bg-background px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{sessionResume.message}</p>
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {getOnboardingSessionResumeStatusLabel(sessionResume.status)}
        </span>
      </div>
      {sessionResume.lastActiveAt ? <p className="mt-1 text-xs text-muted-foreground">Last active {sessionResume.lastActiveAt}</p> : null}
      {sessionResume.canResume && onResume ? (
        <button
          type="button"
          className="mt-3 min-h-10 rounded-full border border-primary/30 bg-primary/10 px-4 text-xs font-semibold text-primary"
          onClick={() => onResume(sessionResume)}
        >
          Resume session
        </button>
      ) : null}
    </div>
  );
}
