import { getOnboardingWorkflowCardVariantLabel, type ContextualWorkflowCardViewModel } from "@/features/onboarding";

interface WorkflowContextCardProps {
  card: ContextualWorkflowCardViewModel;
  onActionSelect?: (label: string, value: string | undefined, position: number) => void;
}

export function WorkflowContextCard({ card, onActionSelect }: WorkflowContextCardProps) {
  return (
    <article className="rounded-xl border border-border/70 bg-background px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{card.title}</p>
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {getOnboardingWorkflowCardVariantLabel(card.variant)}
        </span>
      </div>
      {card.body ? <p className="mt-1 text-xs text-muted-foreground">{card.body}</p> : null}
      {card.actions.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {card.actions.map((action, index) => (
            <button
              key={action.id}
              type="button"
              className="min-h-9 rounded-full border border-border bg-background px-3 text-xs font-medium text-foreground disabled:cursor-not-allowed disabled:opacity-50"
              disabled={action.disabled || !onActionSelect}
              onClick={() => onActionSelect?.(action.label, action.value || undefined, index)}
              aria-label={action.label}
            >
              {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}
