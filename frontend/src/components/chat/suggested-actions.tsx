import type { SuggestedAction } from "@/types";
import { getSuggestedActionsPreview } from "@/features/chat";

interface SuggestedActionsProps {
  actions: SuggestedAction[];
  onActionSelect?: (action: SuggestedAction, position: number) => void;
}

export function SuggestedActions({ actions, onActionSelect }: SuggestedActionsProps) {
  const preview = getSuggestedActionsPreview(actions);

  if (preview.length === 0) return null;

  return (
    <section className="rounded-2xl border border-border/70 bg-muted/40 p-2" aria-label="Suggested actions">
      <div className="flex flex-wrap gap-2">
        {preview.map((action, index) => (
          <button
            key={action.id}
            type="button"
            className="min-h-10 max-w-full truncate rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition hover:border-primary hover:text-primary disabled:opacity-50"
            onClick={() => onActionSelect?.(action, index)}
            disabled={action.disabled}
            title={action.label}
            aria-label={`Suggested action: ${action.label}`}
          >
            {action.label}
          </button>
        ))}
      </div>
    </section>
  );
}
