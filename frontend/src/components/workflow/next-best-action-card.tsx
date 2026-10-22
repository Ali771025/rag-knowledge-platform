import { getOnboardingNextBestActionKindLabel, type OnboardingNextBestActionViewModel } from "@/features/onboarding";

interface NextBestActionCardProps {
  action: OnboardingNextBestActionViewModel;
  position?: number;
  onSelect?: (action: OnboardingNextBestActionViewModel, position: number) => void;
}

export function NextBestActionCard({ action, position = 0, onSelect }: NextBestActionCardProps) {
  const handleSelect = () => {
    if (!onSelect || action.disabled) return;
    onSelect(action, position);
  };

  return (
    <button
      type="button"
      className="w-full rounded-xl border border-border/70 bg-background px-3 py-2 text-left text-sm transition hover:border-primary/50 disabled:cursor-not-allowed disabled:opacity-50"
      disabled={action.disabled || !onSelect}
      onClick={handleSelect}
      aria-label={action.label}
      title={action.label}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-foreground">{action.label}</span>
        <span className="shrink-0 text-[11px] uppercase tracking-wide text-muted-foreground">
          {getOnboardingNextBestActionKindLabel(action.kind)}
        </span>
      </div>
      {action.description ? <p className="mt-1 text-xs text-muted-foreground">{action.description}</p> : null}
    </button>
  );
}
