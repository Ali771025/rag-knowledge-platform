interface ContextualAssistantPanelProps {
  hints?: string[];
  onHintExpanded?: (hintId: string, expanded: boolean) => void;
}

export function ContextualAssistantPanel({ hints = [], onHintExpanded }: ContextualAssistantPanelProps) {
  if (hints.length === 0) {
    return null;
  }

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Contextual assistant">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Assistant context</p>
      <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
        {hints.map((hint, index) => (
          <li key={`${hint}-${index}`}>
            <button
              type="button"
              className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              onClick={() => onHintExpanded?.(`hint-${index}`, true)}
            >
              {hint}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
