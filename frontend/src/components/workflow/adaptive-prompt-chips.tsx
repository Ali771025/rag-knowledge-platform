import { getOnboardingAdaptivePromptKindLabel, type AdaptivePromptItemViewModel } from "@/features/onboarding";

interface AdaptivePromptChipsProps {
  prompts: AdaptivePromptItemViewModel[];
  onPromptSelect?: (prompt: AdaptivePromptItemViewModel, position: number) => void;
}

export function AdaptivePromptChips({ prompts, onPromptSelect }: AdaptivePromptChipsProps) {
  if (prompts.length === 0) {
    return <p className="text-sm text-muted-foreground">No prompt suggestions yet.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2" role="list" aria-label="Adaptive prompt suggestions">
      {prompts.map((prompt, index) => (
        <button
          key={prompt.id}
          type="button"
          className="inline-flex min-h-10 items-center gap-2 rounded-full border border-border bg-background px-3 py-1.5 text-left text-xs font-medium text-foreground transition hover:border-primary/50 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!onPromptSelect}
          onClick={() => onPromptSelect?.(prompt, index)}
          aria-label={prompt.prompt}
          title={prompt.prompt}
        >
          <span className="truncate">{prompt.prompt}</span>
          <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
            {getOnboardingAdaptivePromptKindLabel(prompt.kind)}
          </span>
        </button>
      ))}
    </div>
  );
}
